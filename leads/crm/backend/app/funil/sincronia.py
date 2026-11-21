"""Traz para o funil (crm_negocio) o que o agente grava no banco dele (weap_sdr).

Lê sdr_leads (quem recebeu disparo e como está a conversa) e sdr_fila (quem espera o disparo).
O banco do agente só é lido. Roda no máximo uma vez por minuto, puxada pela tela do funil.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlmodel import Session, select

from app.funil import etapas
from app.leads import repo
from app.models import Negocio, NegocioHistorico, User

log = logging.getLogger(__name__)

INTERVALO_S = 60
_ultima = 0.0

_SQL_LEADS = """
SELECT l.chave, coalesce(l.whatsapp, l.telefone) AS telefone, l.instancia, l.nome_empresa,
       l.status, l.opt_out, l.ia_pausada, l.origem AS origem_agente,
       l.ultimo_contato_em, l.ultima_resposta_em,
       {fila_cols}
  FROM sdr_leads l
  {fila_join}
"""
_FILA_COLS = "f.cnpj, f.cidade, f.nota, f.origem, f.status AS fila_status"
_SEM_FILA = "NULL::text AS cnpj, NULL::text AS cidade, NULL::int AS nota, NULL::text AS origem, NULL::text AS fila_status"
_SQL_SO_FILA = """
SELECT f.chave, f.telefone, f.instancia, f.nome_empresa,
       NULL::text AS status, false AS opt_out, false AS ia_pausada, NULL::text AS origem_agente,
       NULL::timestamptz AS ultimo_contato_em, NULL::timestamptz AS ultima_resposta_em,
       f.cnpj, f.cidade, f.nota, f.origem, f.status AS fila_status
  FROM sdr_fila f
 WHERE f.status IN ('novo', 'pegando')
   AND NOT EXISTS (SELECT 1 FROM sdr_leads l WHERE l.chave = f.chave)
"""


def ler_agente() -> list[dict[str, Any]] | None:
    eng = repo._engine_agente()
    if not eng:
        return None
    with eng.connect() as c:
        tem_fila = c.execute(
            text("SELECT to_regclass('sdr_fila') IS NOT NULL")
        ).scalar()
        sql = _SQL_LEADS.format(
            fila_cols=_FILA_COLS if tem_fila else _SEM_FILA,
            fila_join="LEFT JOIN sdr_fila f ON f.chave = l.chave" if tem_fila else "",
        )
        if tem_fila:
            sql += " UNION ALL " + _SQL_SO_FILA
        return [dict(r._mapping) for r in c.execute(text(sql))]


def _origem(r: dict[str, Any]) -> str:
    if r.get("origem"):
        return str(r["origem"])
    return "trafego" if r.get("origem_agente") == "trafego" else "google_maps"


def _dono_por_numero(session: Session) -> dict[str, Any]:
    """Instância -> id do usuário que tem esse número (o primeiro vendedor, senão qualquer um)."""
    dono: dict[str, Any] = {}
    users = session.exec(select(User).where(User.is_active)).all()
    for u in sorted(users, key=lambda u: u.perfil != "vendedor"):
        for n in u.numeros or []:
            dono.setdefault(n, u.id)
    return dono


def aplicar(session: Session, linhas: list[dict[str, Any]]) -> int:
    """Atualiza o funil com as linhas lidas do agente. Devolve quantos cards mudaram de etapa ou entraram."""
    agora = datetime.now(timezone.utc)
    existentes = {n.chave: n for n in session.exec(select(Negocio)).all()}
    dono = _dono_por_numero(session)
    mudou = 0
    for r in linhas:
        chave = r["chave"]
        if not chave:
            continue
        alvo = etapas.etapa_do_agente(r["status"], bool(r["opt_out"]), r["fila_status"])
        n = existentes.get(chave)
        if n is None:
            if alvo is None:
                continue
            n = Negocio(
                chave=chave,
                etapa=alvo[0],
                perdido_motivo=alvo[1],
                etapa_desde=r["ultimo_contato_em"] or agora,
            )
            session.add(n)
            existentes[chave] = n
            mudou += 1
            session.flush()
            session.add(
                NegocioHistorico(negocio_id=n.id, de=None, para=n.etapa, autor="agente")
            )
        elif alvo and etapas.pode_avancar(n.etapa, alvo[0]):
            session.add(
                NegocioHistorico(
                    negocio_id=n.id, de=n.etapa, para=alvo[0], autor="agente"
                )
            )
            n.etapa, n.etapa_desde = alvo[0], agora
            if alvo[1]:
                n.perdido_motivo = alvo[1]
            mudou += 1
        n.telefone = r["telefone"] or n.telefone
        n.nome = r["nome_empresa"] or n.nome or chave
        n.instancia = r["instancia"] or n.instancia
        n.status_agente = r["status"] or n.status_agente
        n.ia_pausada = bool(r["ia_pausada"]) or r["status"] == "humano"
        n.ultimo_contato_em = r["ultimo_contato_em"] or n.ultimo_contato_em
        n.ultima_resposta_em = r["ultima_resposta_em"] or n.ultima_resposta_em
        n.cnpj = n.cnpj or r["cnpj"]
        n.cidade = n.cidade or r["cidade"]
        if r["nota"] is not None:
            n.nota = r["nota"]
        n.origem = _origem(r)
        if n.responsavel_id is None and n.instancia in dono:
            n.responsavel_id = dono[n.instancia]
        n.atualizado_em = agora
    session.commit()
    return mudou


def sincronizar(session: Session, forcar: bool = False) -> bool:
    """Sincroniza se passou 1 minuto da última vez. Só um processo por vez (trava no banco do CRM)."""
    global _ultima
    if not forcar and time.monotonic() - _ultima < INTERVALO_S:
        return False
    _ultima = time.monotonic()
    if not session.execute(text("SELECT pg_try_advisory_xact_lock(4242)")).scalar():
        return False
    try:
        linhas = ler_agente()
    except Exception:
        log.exception("não consegui ler o banco do agente")
        session.rollback()
        return False
    if linhas is None:
        session.rollback()
        return False
    aplicar(session, linhas)
    return True
