"""Nota dos leads guardada em receita.notas, para a busca não calcular a nota de
1,4 milhão de empresas toda vez que abre.

A tabela tem uma linha por estabelecimento, com a nota de cada oferta
(nota_geral, nota_site...), o celular e a data de abertura, e um índice por
oferta na ordem da busca. Ela é refeita sozinha, em segundo plano, quando muda
algo que mexe na nota:
- a importação mensal (que termina com ANALYZE em receita.estabelecimentos);
- a lista de clientes atuais (receita.clientes_weap);
- as cidades atendidas (CIDADES_ATENDIDAS) ou o cálculo da nota no código.
Durante o recálculo a busca usa a tabela anterior. Se ainda não existe
nenhuma (primeira vez), calcula a nota na hora, como antes.
"""

import hashlib
import logging
import threading
import time

from sqlalchemy import text
from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine

log = logging.getLogger(__name__)

TRAVA = 4243  # pg_advisory_lock: um só recálculo por vez, entre os processos
CHECAR_A_CADA = 60  # segundos

_estado: dict[str, float | bool] = {"pronta": False, "checado": 0.0}
_rodando = threading.Lock()


def _marca(s: Session) -> str:
    """O que, se mudar, muda a nota."""
    from app.leads import repo

    base = s.execute(
        text(
            """SELECT coalesce((SELECT last_analyze::text FROM pg_stat_user_tables
                                 WHERE schemaname = 'receita' AND relname = 'estabelecimentos'), '')
                   || '|' ||
                   coalesce((SELECT md5(string_agg(coalesce(cnpj, '') || ':' || array_to_string(ofertas, ','),
                                                   ';' ORDER BY nome, cnpj))
                               FROM receita.clientes_weap), '')"""
        )
    ).scalar_one()
    codigo = repo._nota_expr() + repr(sorted(repo.OFERTAS)) + settings.CIDADES_ATENDIDAS
    return hashlib.md5((base + "|" + codigo).encode()).hexdigest()


def _existe(s: Session) -> bool:
    return bool(
        s.execute(
            text(
                "SELECT to_regclass('receita.notas') IS NOT NULL "
                "AND to_regclass('receita.notas_info') IS NOT NULL"
            )
        ).scalar()
    )


def _em_dia(s: Session) -> bool:
    ok = s.execute(
        text(
            "SELECT to_regclass('receita.notas') IS NOT NULL "
            "AND to_regclass('receita.notas_info') IS NOT NULL"
        )
    ).scalar()
    if not ok:
        return False
    feita = s.execute(
        text("SELECT marca FROM receita.notas_info WHERE id = 1")
    ).scalar()
    return feita == _marca(s)


def coluna(s: Session, oferta: str) -> str | None:
    """Coluna da nota da oferta em receita.notas, ou None se a tabela ainda não
    existe. Se ela não está em dia, começa o recálculo em segundo plano."""
    agora = time.monotonic()
    if agora - _estado["checado"] > CHECAR_A_CADA:
        em_dia = False
        try:
            _estado["pronta"] = _existe(s)
            em_dia = bool(_estado["pronta"]) and _em_dia(s)
        except Exception:
            log.exception("não deu para conferir a tabela de notas")
            s.rollback()
            _estado["pronta"] = False
        _estado["checado"] = agora
        if not em_dia:
            em_segundo_plano()
    return f"nota_{oferta}" if _estado["pronta"] else None


def em_segundo_plano() -> None:
    if _rodando.locked():
        return
    threading.Thread(target=_recalcular_seguro, daemon=True).start()


def _recalcular_seguro() -> None:
    if not _rodando.acquire(blocking=False):
        return
    try:
        recalcular()
    except Exception:
        log.exception("recálculo das notas falhou")
    finally:
        _rodando.release()


def recalcular() -> bool:
    """Refaz receita.notas. Devolve False se outro processo já está refazendo."""
    from app.leads import repo

    with Session(engine) as s:
        if not s.execute(
            text("SELECT pg_try_advisory_lock(:t)"), {"t": TRAVA}
        ).scalar():
            return False
        try:
            inicio = time.monotonic()
            if _em_dia(s):
                return True
            marca = _marca(s)
            p: dict[str, object] = {"atende_cod": repo._atende(s)}
            for o in repo.OFERTAS:
                p |= repo._perfil(s, o, f"_{o}")
            notas = ",\n".join(
                f"({repo._nota_expr(f'_{o}')})::smallint AS nota_{o}"
                for o in repo.OFERTAS
            )
            s.execute(text("DROP TABLE IF EXISTS receita.notas_nova"))
            s.execute(
                text(
                    f"""CREATE TABLE receita.notas_nova AS
                        SELECT e.cnpj, e.data_abertura, x.cel AS celular,
                               {notas.replace(repo.CELULAR, "x.cel")}
                          FROM receita.estabelecimentos e
                          JOIN receita.empresas emp ON emp.cnpj_basico = e.cnpj_basico
                          CROSS JOIN LATERAL (SELECT {repo.CELULAR} AS cel) x"""
                ),
                p,
            )
            sufixo = str(int(time.time()))
            s.execute(
                text(
                    f"CREATE UNIQUE INDEX notas_cnpj_{sufixo} ON receita.notas_nova (cnpj)"
                )
            )
            for o in repo.OFERTAS:
                s.execute(
                    text(
                        f"CREATE INDEX notas_{o}_{sufixo} ON receita.notas_nova "
                        f"(nota_{o} DESC, data_abertura DESC NULLS LAST, cnpj)"
                    )
                )
            s.execute(text("ANALYZE receita.notas_nova"))
            s.commit()
            # troca a tabela velha pela nova de uma vez
            s.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS receita.notas_info "
                    "(id int PRIMARY KEY, marca text NOT NULL, feito_em timestamptz NOT NULL)"
                )
            )
            s.execute(text("DROP TABLE IF EXISTS receita.notas"))
            s.execute(text("ALTER TABLE receita.notas_nova RENAME TO notas"))
            s.execute(
                text(
                    "INSERT INTO receita.notas_info VALUES (1, :m, now()) "
                    "ON CONFLICT (id) DO UPDATE SET marca = :m, feito_em = now()"
                ),
                {"m": marca},
            )
            s.commit()
            _estado["checado"] = 0.0
            log.info("notas recalculadas em %.0f s", time.monotonic() - inicio)
            return True
        finally:
            s.rollback()
            s.execute(text("SELECT pg_advisory_unlock(:t)"), {"t": TRAVA})
            s.commit()
