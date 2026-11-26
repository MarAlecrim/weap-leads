"""Consultas na base da Receita (schema receita) e a nota de cada lead.

A nota (0 a 100) mede o quanto a empresa se parece com quem já comprou a oferta
escolhida (view receita.perfil_oferta, montada a partir de receita.clientes_weap).
"""

import logging
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.core.config import settings
from app.leads import notas, texto

log = logging.getLogger(__name__)

LIMITE_PLANILHA = 3000
POR_PAGINA = 50

# Pesos da nota. Somam 100.
PESOS = {
    "regiao": 25,  # mesma cidade dos clientes, ou região onde a Weap atende
    "dono": 20,  # 1 a 3 sócios: quem atende é quem decide
    "celular": 20,  # dá para chamar no WhatsApp
    "ramo": 15,  # mesmo ramo (divisão do CNAE) de algum cliente
    "porte": 10,  # mesmo porte de algum cliente
    "email": 5,
    "idade": 5,  # idade dentro da faixa dos clientes
}

MOTIVOS = {
    "regiao": "região onde a Weap já atende",
    "dono": "dono decide (1 a 3 sócios)",
    "celular": "tem celular (WhatsApp)",
    "ramo": "mesmo ramo de clientes atuais",
    "porte": "mesmo porte de clientes atuais",
    "email": "tem e-mail",
    "idade": "idade parecida com a dos clientes",
}

OFERTAS = {
    "geral": "Todos os serviços",
    "site": "Site",
    "redes": "Redes sociais",
    "sdr": "Automação SDR / WhatsApp",
    "simplestv": "SimplesTV (painel)",
    "manutencao": "Manutenção e serviços técnicos",
    "blog": "Blog com IA",
    "sistema": "Sistemas",
}


@dataclass
class Filtros:
    oferta: str = "geral"
    nicho: str = ""
    secundario: bool = False
    uf: str = ""
    cidade: str = ""
    bairro: str = ""
    nome: str = ""
    porte: list[str] = field(default_factory=list)
    capital_min: float | None = None
    capital_max: float | None = None
    anos_min: int | None = None
    anos_max: int | None = None
    celular: bool = True
    email: bool = False
    socio: bool = False
    nota_min: int | None = None
    esconder_disparo: bool = False


CELULAR = "(receita.celular(e.telefone1) OR receita.celular(e.telefone2))"


def _where(f: Filtros, s: Session) -> tuple[str, dict[str, Any]]:
    w: list[str] = []
    p: dict[str, Any] = {}
    if f.nicho:
        cnaes = [
            r[0]
            for r in s.execute(
                text("SELECT cnae FROM receita.nicho_cnaes WHERE nicho = :n"),
                {"n": f.nicho},
            )
        ] or ["0"]
        p["cnaes"] = cnaes
        w.append(
            "(e.cnae_principal = ANY(:cnaes) OR e.cnaes_secundarios && CAST(:cnaes AS text[]))"
            if f.secundario
            else "e.cnae_principal = ANY(:cnaes)"
        )
    if f.uf:
        w.append("e.uf = :uf")
        p["uf"] = f.uf
    if f.cidade:
        w.append("e.municipio = :cidade")
        p["cidade"] = f.cidade
    if f.bairro:
        w.append("unaccent(e.bairro) ILIKE unaccent(:bairro)")
        p["bairro"] = f"%{f.bairro}%"
    if f.nome:
        w.append(
            "(unaccent(e.nome_fantasia) ILIKE unaccent(:nome) OR unaccent(emp.razao_social) ILIKE unaccent(:nome))"
        )
        p["nome"] = f"%{f.nome}%"
    faixas = {
        "mei": "coalesce(si.mei, false)",
        "me": "(emp.porte = '01' AND NOT coalesce(si.mei, false))",
        "epp": "emp.porte = '03'",
        "media": "(emp.porte = '05' AND coalesce(emp.capital_social, 0) <= :cap_grande)",
        "grande": "(emp.porte = '05' AND emp.capital_social > :cap_grande)",
    }
    escolhidas = [faixas[x] for x in dict.fromkeys(f.porte) if x in faixas]
    if escolhidas:
        w.append("(" + " OR ".join(escolhidas) + ")")
        if any(x in ("media", "grande") for x in f.porte):
            p["cap_grande"] = texto.CAPITAL_GRANDE
    if f.capital_min is not None:
        w.append("coalesce(emp.capital_social, 0) >= :cmin")
        p["cmin"] = f.capital_min
    if f.capital_max is not None:
        w.append("coalesce(emp.capital_social, 0) <= :cmax")
        p["cmax"] = f.capital_max
    if f.anos_min is not None:
        w.append("e.data_abertura <= current_date - make_interval(years => :amin)")
        p["amin"] = max(0, f.anos_min)
    if f.anos_max is not None:
        w.append("e.data_abertura >= current_date - make_interval(years => :amax)")
        p["amax"] = max(0, f.anos_max)
    if f.celular:
        w.append(CELULAR)
    if f.email:
        w.append("e.email LIKE '%@%'")
    if f.socio:
        w.append(
            "EXISTS (SELECT 1 FROM receita.socios so WHERE so.cnpj_basico = e.cnpj_basico AND so.tipo = '2')"
        )
    return (" AND ".join(w) or "true"), p


def _partes(suf: str = "") -> dict[str, str]:
    """Condições de cada critério da nota. O perfil da oferta vem por parâmetro
    (:mun, :div, :por, :amin, :amax, com o sufixo da oferta) e :atende_cod são os
    códigos das cidades onde a Weap atende."""
    return {
        "regiao": f"(e.municipio = ANY(CAST(:mun{suf} AS text[])) OR e.municipio = ANY(CAST(:atende_cod AS text[])))",
        "dono": "coalesce(emp.n_socios, 0) BETWEEN 1 AND 3",
        "celular": CELULAR,
        "ramo": f"left(e.cnae_principal, 2) = ANY(CAST(:div{suf} AS text[]))",
        "porte": f"emp.porte = ANY(CAST(:por{suf} AS text[]))",
        "email": "coalesce(e.email, '') LIKE '%@%'",
        "idade": f"extract(year FROM age(current_date, e.data_abertura)) BETWEEN CAST(:amin{suf} AS int) AND CAST(:amax{suf} AS int)",
    }


def _nota_expr(suf: str = "") -> str:
    return " + ".join(
        f"(CASE WHEN {c} THEN {PESOS[k]} ELSE 0 END)" for k, c in _partes(suf).items()
    )


def _motivos_expr(suf: str = "") -> str:
    motivos = ", ".join(
        f"CASE WHEN {c} THEN '{k}' END" for k, c in _partes(suf).items()
    )
    return f"array_remove(ARRAY[{motivos}], NULL)"


COLUNAS = """
  SELECT e.cnpj, e.cnpj_basico,
         coalesce(nullif(e.nome_fantasia, ''), emp.razao_social) AS nome,
         emp.razao_social, emp.porte, emp.capital_social, coalesce(emp.n_socios, 0) AS n_socios,
         coalesce(si.mei, false) AS mei, coalesce(si.simples, false) AS simples,
         e.data_abertura, e.cnae_principal, c.descricao AS atividade,
         e.logradouro, e.numero, e.complemento, e.bairro, e.cep,
         cid.nome AS cidade, e.uf, e.telefone1, e.telefone2, e.email,
         (SELECT s.nome FROM receita.socios s
           WHERE s.cnpj_basico = e.cnpj_basico AND s.tipo = '2'
           ORDER BY (s.qualificacao IN ('49','05','16')) DESC, s.data_entrada LIMIT 1) AS decisor,
"""

JUNTA = """
    JOIN receita.empresas emp ON emp.cnpj_basico = e.cnpj_basico
    LEFT JOIN receita.simples si ON si.cnpj_basico = e.cnpj_basico
    LEFT JOIN receita.cnaes c ON c.codigo = e.cnae_principal
    LEFT JOIN receita.cidades cid ON cid.municipio = e.municipio
"""

# nota calculada na hora (sem a tabela receita.notas)
SELECT = f"""{COLUNAS}
         ({_nota_expr()}) AS nota, {_motivos_expr()} AS motivos
    FROM receita.estabelecimentos e {JUNTA}"""


def _select_notas(col: str) -> str:
    """Mesmas colunas, com a nota já guardada em receita.notas (ver notas.py)."""
    return f"""{COLUNAS}
         n.{col} AS nota, {_motivos_expr()} AS motivos
    FROM receita.notas n
    JOIN receita.estabelecimentos e ON e.cnpj = n.cnpj {JUNTA}"""


def _atende(s: Session) -> list[str]:
    nomes = [
        c.strip().upper() for c in settings.CIDADES_ATENDIDAS.split(",") if c.strip()
    ]
    return [
        r[0]
        for r in s.execute(
            text("SELECT codigo FROM receita.municipios WHERE nome = ANY(:n)"),
            {"n": nomes},
        )
    ]


def _perfil(s: Session, oferta: str, suf: str = "") -> dict[str, Any]:
    r = (
        s.execute(
            text(
                "SELECT municipios, divisoes, portes, anos_min, anos_max "
                "FROM receita.perfil_oferta WHERE oferta = :o"
            ),
            {"o": oferta},
        )
        .mappings()
        .first()
    )
    return {
        f"mun{suf}": list(r["municipios"] or []) if r else [],
        f"div{suf}": list(r["divisoes"] or []) if r else [],
        f"por{suf}": list(r["portes"] or []) if r else [],
        f"amin{suf}": r["anos_min"] if r else None,
        f"amax{suf}": r["anos_max"] if r else None,
    }


def _oferta(f: Filtros) -> str:
    return f.oferta if f.oferta in OFERTAS else "geral"


def _params_base(f: Filtros, s: Session) -> dict[str, Any]:
    return _perfil(s, _oferta(f)) | {"atende_cod": _atende(s)}


def _linha(r: dict[str, Any], no_disparo: set[str]) -> dict[str, Any]:
    zap = texto.whatsapp(r["telefone1"], r["telefone2"])
    chaves = {texto.chave(r["telefone1"]), texto.chave(r["telefone2"])} - {None}
    return {
        "cnpj": r["cnpj"],
        "nome": texto.nome_bonito(r["nome"]),
        "razao_social": texto.nome_bonito(r["razao_social"]),
        "atividade": r["atividade"] or "",
        "cnae": r["cnae_principal"],
        "porte": texto.FAIXAS.get(
            texto.faixa(r["porte"], r["mei"], r["capital_social"]), "Não informado"
        ),
        "simples": bool(r["simples"]),
        "capital_social": float(r["capital_social"] or 0),
        "anos": texto.anos(r["data_abertura"]),
        "bairro": texto.nome_bonito(r["bairro"]),
        "cidade": texto.nome_bonito(r["cidade"]),
        "uf": r["uf"],
        "endereco": texto.endereco(r),
        "telefone1": texto.fone_bonito(r["telefone1"]),
        "telefone2": texto.fone_bonito(r["telefone2"]),
        "whatsapp": zap,
        "email": r["email"] or "",
        "decisor": texto.nome_bonito(r["decisor"]),
        "n_socios": r["n_socios"],
        "nota": int(r["nota"]),
        "motivos": [MOTIVOS[m] for m in r["motivos"]],
        "no_disparo": bool(chaves & no_disparo),
    }


@lru_cache(maxsize=1)
def _engine_agente() -> Engine | None:
    if not settings.AGENTE_DB_URL:
        return None
    # no máximo 4 conexões por processo (2 processos): o usuário leads_crm tem limite no banco do agente
    return create_engine(
        settings.AGENTE_DB_URL, pool_pre_ping=True, pool_size=2, max_overflow=2
    )


def chaves_no_disparo(chaves: set[str]) -> set[str]:
    """Quais telefones já estão no banco do agente (weap_sdr): contatados ou na fila do disparo.
    Sem conexão, devolve vazio."""
    eng = _engine_agente()
    if not eng or not chaves:
        return set()
    try:
        with eng.connect() as c:
            k = {"k": list(chaves)}
            achou = {
                r[0]
                for r in c.execute(
                    text("SELECT chave FROM sdr_leads WHERE chave = ANY(:k)"), k
                )
            }
            if c.execute(text("SELECT to_regclass('sdr_fila') IS NOT NULL")).scalar():
                achou |= {
                    r[0]
                    for r in c.execute(
                        text("SELECT chave FROM sdr_fila WHERE chave = ANY(:k)"), k
                    )
                }
            return achou
    except Exception:  # banco do agente fora do ar não pode derrubar a busca
        log.exception("Falha ao consultar o banco do agente")
        return set()


class SemBancoDoAgente(RuntimeError):
    """O CRM não está ligado ao banco do agente (AGENTE_DB_URL vazio)."""


def mandar_para_fila(linhas: list[dict[str, Any]], criado_por: str) -> dict[str, int]:
    """Coloca os leads na fila do disparo (sdr_fila). Quem já está no disparo ou na fila fica de fora."""
    eng = _engine_agente()
    if not eng:
        raise SemBancoDoAgente()
    sem_zap = sum(1 for r in linhas if not r["whatsapp"])
    ja = sum(1 for r in linhas if r["whatsapp"] and r["no_disparo"])
    novos = [r for r in linhas if r["whatsapp"] and not r["no_disparo"]]
    adicionados = 0
    if novos:
        with eng.begin() as c:
            rs = c.execute(
                text(
                    """INSERT INTO sdr_fila (chave, telefone, nome_empresa, endereco, cidade, uf, especialidades,
                                            decisor, email, cnpj, nota, origem, criado_por)
                       SELECT sdr_chave(t), t || '@s.whatsapp.net', n, en, ci, nullif(u, ''), es, de, em, cn, no, 'receita', :por
                         FROM unnest(CAST(:t AS text[]), CAST(:n AS text[]), CAST(:en AS text[]),
                                     CAST(:ci AS text[]), CAST(:u AS text[]), CAST(:es AS text[]), CAST(:de AS text[]),
                                     CAST(:em AS text[]), CAST(:cn AS text[]), CAST(:no AS int[]))
                              AS x(t, n, en, ci, u, es, de, em, cn, no)
                        WHERE sdr_chave(t) IS NOT NULL
                       ON CONFLICT (chave) DO NOTHING
                       RETURNING id"""
                ),
                {
                    "t": ["55" + r["whatsapp"] for r in novos],
                    "n": [r["nome"] for r in novos],
                    "en": [r["endereco"] for r in novos],
                    "ci": [r["cidade"] for r in novos],
                    "u": [r.get("uf") or "" for r in novos],
                    "es": [r["atividade"] for r in novos],
                    "de": [r["decisor"] for r in novos],
                    "em": [r["email"] for r in novos],
                    "cn": [r["cnpj"] for r in novos],
                    "no": [r["nota"] for r in novos],
                    "por": criado_por,
                },
            )
            adicionados = len(rs.fetchall())
    return {
        "adicionados": adicionados,
        "ja_no_disparo": ja + (len(novos) - adicionados),
        "sem_whatsapp": sem_zap,
    }


def resumo_fila() -> dict[str, int] | None:
    """Quantos leads há em cada situação da fila do disparo. None se o banco do agente não estiver ligado."""
    eng = _engine_agente()
    if not eng:
        return None
    try:
        with eng.connect() as c:
            if not c.execute(
                text("SELECT to_regclass('sdr_fila') IS NOT NULL")
            ).scalar():
                return None
            r = (
                c.execute(
                    text(
                        """SELECT count(*) FILTER (WHERE status = 'novo') AS aguardando,
                              count(*) FILTER (WHERE status = 'pegando') AS enviando,
                              count(*) FILTER (WHERE status = 'enviado'
                                 AND enviado_em >= date_trunc('day', now() AT TIME ZONE 'America/Sao_Paulo')
                                                   AT TIME ZONE 'America/Sao_Paulo') AS enviados_hoje,
                              count(*) FILTER (WHERE status = 'enviado') AS enviados,
                              count(*) FILTER (WHERE status IN ('pulado', 'erro')) AS pulados
                         FROM sdr_fila"""
                    )
                )
                .mappings()
                .one()
            )
            return {k: int(v) for k, v in r.items()}
    except Exception:
        log.exception("Falha ao ler a fila do disparo")
        return None


def _marca(linhas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chaves = {
        k
        for r in linhas
        for k in (texto.chave(r["telefone1"]), texto.chave(r["telefone2"]))
        if k
    }
    no = chaves_no_disparo(chaves)
    return [_linha(r, no) for r in linhas]


def _consulta(s: Session, f: Filtros, w: str, limite: str) -> tuple[str, str | None]:
    """Monta a consulta da página e, quando a tabela de notas está em dia, a
    contagem rápida. Devolve (consulta, coluna da nota ou None)."""
    col = notas.coluna(s, _oferta(f))
    if col:
        if f.nota_min:
            w += f" AND n.{col} >= {int(f.nota_min)}"
        # celular vem pronto em notas.celular: deixa o índice da nota trabalhar
        w = w.replace(CELULAR, "n.celular")
        return (
            f"{_select_notas(col)} WHERE {w} "
            f"ORDER BY n.{col} DESC, n.data_abertura DESC NULLS LAST, n.cnpj {limite}",
            col,
        )
    nota_min = f"WHERE nota >= {int(f.nota_min)}" if f.nota_min else ""
    return (
        f"SELECT * FROM ({SELECT} WHERE {w}) x {nota_min} "
        f"ORDER BY nota DESC, data_abertura DESC NULLS LAST, cnpj {limite}",
        None,
    )


def _total(s: Session, f: Filtros, w: str, p: dict[str, Any], col: str | None) -> int:
    if col is None:
        nota_min = f"WHERE nota >= {int(f.nota_min)}" if f.nota_min else ""
        return int(
            s.execute(
                text(f"SELECT count(*) FROM ({SELECT} WHERE {w}) x {nota_min}"), p
            ).scalar_one()
        )
    conds = [] if w == "true" else w.split(" AND ")
    nmin = [f"n.{col} >= {int(f.nota_min)}"] if f.nota_min else []
    if all(c == CELULAR for c in conds):
        # sem filtro além do celular: conta só na tabela de notas (rápido)
        where = " AND ".join((["n.celular"] if conds else []) + nmin) or "true"
        return int(
            s.execute(
                text(f"SELECT count(*) FROM receita.notas n WHERE {where}")
            ).scalar_one()
        )
    where = " AND ".join([w.replace(CELULAR, "n.celular"), *nmin])
    return int(
        s.execute(
            text(
                f"""SELECT count(*) FROM receita.notas n
                     JOIN receita.estabelecimentos e ON e.cnpj = n.cnpj
                     JOIN receita.empresas emp ON emp.cnpj_basico = e.cnpj_basico
                     LEFT JOIN receita.simples si ON si.cnpj_basico = e.cnpj_basico
                    WHERE {where}"""
            ),
            p,
        ).scalar_one()
    )


def buscar(s: Session, f: Filtros, pagina: int = 1) -> tuple[list[dict[str, Any]], int]:
    w, p = _where(f, s)
    p |= _params_base(f, s)
    sql, col = _consulta(s, f, w, "LIMIT :lim OFFSET :off")
    total = _total(s, f, w, p, col)
    p |= {
        "lim": POR_PAGINA * (4 if f.esconder_disparo else 1),
        "off": (max(pagina, 1) - 1) * POR_PAGINA,
    }
    rs = s.execute(text(sql), p).mappings()
    linhas = _marca([dict(r) for r in rs])
    if f.esconder_disparo:
        linhas = [r for r in linhas if not r["no_disparo"]][:POR_PAGINA]
    return linhas, total


def para_planilha(
    s: Session, f: Filtros, cnpjs: list[str] | None = None
) -> list[dict[str, Any]]:
    w, p = _where(f, s)
    p |= _params_base(f, s)
    if cnpjs:
        w += " AND e.cnpj = ANY(:cnpjs)"
        p["cnpjs"] = [c.upper() for c in cnpjs]
    sql, _ = _consulta(s, f, w, f"LIMIT {LIMITE_PLANILHA}")
    rs = s.execute(text(sql), p).mappings()
    return _marca([dict(r) for r in rs])


def ficha(s: Session, cnpj: str, oferta: str = "geral") -> dict[str, Any] | None:
    p = _params_base(Filtros(oferta=oferta), s) | {"cnpj": cnpj.upper()}
    r = s.execute(text(f"{SELECT} WHERE e.cnpj = :cnpj"), p).mappings().first()
    if not r:
        return None
    lead = _marca([dict(r)])[0]
    socios = s.execute(
        text(
            """SELECT s.nome, s.tipo, s.data_entrada, s.faixa_etaria,
                      coalesce(q.descricao, s.qualificacao) AS qualificacao,
                      s.qualificacao IN ('49','05','16') AS administra
                 FROM receita.socios s
                 LEFT JOIN receita.qualificacoes q ON q.codigo = s.qualificacao
                WHERE s.cnpj_basico = :b
                ORDER BY (s.qualificacao IN ('49','05','16')) DESC, s.data_entrada"""
        ),
        {"b": r["cnpj_basico"]},
    ).mappings()
    lead["socios"] = [
        {
            "nome": texto.nome_bonito(x["nome"]),
            "pessoa_fisica": x["tipo"] == "2",
            "qualificacao": x["qualificacao"] or "",
            "desde": x["data_entrada"].isoformat() if x["data_entrada"] else None,
            "administra": bool(x["administra"]),
        }
        for x in socios
    ]
    return lead


def nichos(s: Session) -> list[dict[str, str]]:
    rs = s.execute(
        text("SELECT DISTINCT nicho FROM receita.nicho_cnaes ORDER BY nicho")
    )
    return [{"id": r[0], "nome": texto.nome_nicho(r[0])} for r in rs]


def cidades(s: Session) -> list[dict[str, Any]]:
    rs = s.execute(
        text(
            "SELECT municipio, nome, uf, empresas FROM receita.cidades "
            "WHERE nome IS NOT NULL ORDER BY empresas DESC"
        )
    ).mappings()
    return [
        {
            "id": r["municipio"],
            "nome": f"{texto.nome_bonito(r['nome'])} - {r['uf']}",
            "uf": r["uf"],
            "empresas": r["empresas"],
        }
        for r in rs
    ]


def clientes(s: Session) -> list[dict[str, Any]]:
    rs = s.execute(
        text(
            """SELECT c.nome, c.ofertas, c.ativo, c.valor_cents, c.cnpj,
                      pc.cnae_descricao, pc.porte, pc.capital_social, pc.anos, pc.cidade, pc.uf,
                      pc.socios, pc.achou_na_receita,
                      coalesce((SELECT si.mei FROM receita.simples si
                                 WHERE si.cnpj_basico = left(c.cnpj, 8)), false) AS mei
                 FROM receita.clientes_weap c
                 JOIN receita.perfil_clientes pc ON pc.nome = c.nome
                ORDER BY c.ativo DESC, c.nome"""
        )
    ).mappings()
    return [
        {
            "nome": r["nome"],
            "ofertas": [OFERTAS.get(o, o) for o in r["ofertas"] if o != "hospedagem"],
            "ativo": r["ativo"],
            "valor": (r["valor_cents"] or 0) / 100,
            "cnpj": r["cnpj"],
            "atividade": r["cnae_descricao"] or "",
            "porte": texto.FAIXAS.get(
                texto.faixa(r["porte"], r["mei"], r["capital_social"]), ""
            )
            if r["achou_na_receita"]
            else "",
            "anos": r["anos"],
            "cidade": texto.nome_bonito(r["cidade"]),
            "socios": r["socios"],
            "achou": r["achou_na_receita"],
        }
        for r in rs
    ]


def perfis(s: Session) -> list[dict[str, Any]]:
    rs = s.execute(
        text("SELECT oferta, clientes FROM receita.perfil_oferta")
    ).mappings()
    qtd = {r["oferta"]: r["clientes"] for r in rs}
    return [{"id": k, "nome": v, "clientes": qtd.get(k, 0)} for k, v in OFERTAS.items()]
