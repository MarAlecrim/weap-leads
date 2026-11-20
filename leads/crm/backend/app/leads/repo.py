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
from app.leads import texto

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
    cidade: str = ""
    bairro: str = ""
    nome: str = ""
    porte: list[str] = field(default_factory=list)
    anos_min: int | None = None
    anos_max: int | None = None
    celular: bool = True
    email: bool = False
    socio: bool = False
    nota_min: int | None = None
    esconder_disparo: bool = False


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
    portes = [x for x in f.porte if x in texto.PORTES]
    if portes:
        w.append("emp.porte = ANY(:portes)")
        p["portes"] = portes
    if f.anos_min is not None:
        w.append("e.data_abertura <= current_date - make_interval(years => :amin)")
        p["amin"] = max(0, f.anos_min)
    if f.anos_max is not None:
        w.append("e.data_abertura >= current_date - make_interval(years => :amax)")
        p["amax"] = max(0, f.anos_max)
    if f.celular:
        w.append("(receita.celular(e.telefone1) OR receita.celular(e.telefone2))")
    if f.email:
        w.append("e.email LIKE '%@%'")
    if f.socio:
        w.append(
            "EXISTS (SELECT 1 FROM receita.socios so WHERE so.cnpj_basico = e.cnpj_basico AND so.tipo = '2')"
        )
    return (" AND ".join(w) or "true"), p


def _nota_sql() -> str:
    t = PESOS
    partes = {
        "regiao": "(e.municipio = ANY(coalesce(pf.municipios, '{}')) OR e.municipio IN (SELECT codigo FROM receita.municipios WHERE nome = ANY(:atende)))",
        "dono": "coalesce(emp.n_socios, 0) BETWEEN 1 AND 3",
        "celular": "(receita.celular(e.telefone1) OR receita.celular(e.telefone2))",
        "ramo": "left(e.cnae_principal, 2) = ANY(coalesce(pf.divisoes, '{}'))",
        "porte": "emp.porte = ANY(coalesce(pf.portes, '{}'))",
        "email": "coalesce(e.email, '') LIKE '%@%'",
        "idade": "extract(year FROM age(current_date, e.data_abertura)) BETWEEN pf.anos_min AND pf.anos_max",
    }
    soma = " + ".join(
        f"(CASE WHEN {c} THEN {t[k]} ELSE 0 END)" for k, c in partes.items()
    )
    motivos = ", ".join(f"CASE WHEN {c} THEN '{k}' END" for k, c in partes.items())
    return f"({soma}) AS nota, array_remove(ARRAY[{motivos}], NULL) AS motivos"


SELECT = f"""
  SELECT e.cnpj, e.cnpj_basico,
         coalesce(nullif(e.nome_fantasia, ''), emp.razao_social) AS nome,
         emp.razao_social, emp.porte, emp.capital_social, coalesce(emp.n_socios, 0) AS n_socios,
         e.data_abertura, e.cnae_principal, c.descricao AS atividade,
         e.logradouro, e.numero, e.complemento, e.bairro, e.cep,
         cid.nome AS cidade, e.uf, e.telefone1, e.telefone2, e.email,
         (SELECT s.nome FROM receita.socios s
           WHERE s.cnpj_basico = e.cnpj_basico AND s.tipo = '2'
           ORDER BY (s.qualificacao IN ('49','05','16')) DESC, s.data_entrada LIMIT 1) AS decisor,
         {_nota_sql()}
    FROM receita.estabelecimentos e
    JOIN receita.empresas emp ON emp.cnpj_basico = e.cnpj_basico
    LEFT JOIN receita.cnaes c ON c.codigo = e.cnae_principal
    LEFT JOIN receita.cidades cid ON cid.municipio = e.municipio
    LEFT JOIN receita.perfil_oferta pf ON pf.oferta = :oferta
"""


def _params_base(f: Filtros) -> dict[str, Any]:
    return {
        "oferta": f.oferta if f.oferta in OFERTAS else "geral",
        "atende": [
            c.strip().upper()
            for c in settings.CIDADES_ATENDIDAS.split(",")
            if c.strip()
        ],
    }


def _linha(r: dict[str, Any], no_disparo: set[str]) -> dict[str, Any]:
    zap = texto.whatsapp(r["telefone1"], r["telefone2"])
    chaves = {texto.chave(r["telefone1"]), texto.chave(r["telefone2"])} - {None}
    return {
        "cnpj": r["cnpj"],
        "nome": texto.nome_bonito(r["nome"]),
        "razao_social": texto.nome_bonito(r["razao_social"]),
        "atividade": r["atividade"] or "",
        "cnae": r["cnae_principal"],
        "porte": texto.PORTES.get(r["porte"] or "00", "Não informado"),
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
    return create_engine(settings.AGENTE_DB_URL, pool_pre_ping=True, pool_size=2)


def chaves_no_disparo(chaves: set[str]) -> set[str]:
    """Quais telefones já estão no banco do agente (weap_sdr). Sem conexão, devolve vazio."""
    eng = _engine_agente()
    if not eng or not chaves:
        return set()
    try:
        with eng.connect() as c:
            rs = c.execute(
                text("SELECT chave FROM sdr_leads WHERE chave = ANY(:k)"),
                {"k": list(chaves)},
            )
            return {r[0] for r in rs}
    except Exception:  # banco do agente fora do ar não pode derrubar a busca
        log.exception("Falha ao consultar o banco do agente")
        return set()


def _marca(linhas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chaves = {
        k
        for r in linhas
        for k in (texto.chave(r["telefone1"]), texto.chave(r["telefone2"]))
        if k
    }
    no = chaves_no_disparo(chaves)
    return [_linha(r, no) for r in linhas]


def buscar(s: Session, f: Filtros, pagina: int = 1) -> tuple[list[dict[str, Any]], int]:
    w, p = _where(f, s)
    p |= _params_base(f)
    nota_min = f"WHERE nota >= {int(f.nota_min)}" if f.nota_min else ""
    total = s.execute(
        text(f"SELECT count(*) FROM ({SELECT} WHERE {w}) x {nota_min}"), p
    ).scalar_one()
    p |= {
        "lim": POR_PAGINA * (4 if f.esconder_disparo else 1),
        "off": (max(pagina, 1) - 1) * POR_PAGINA,
    }
    rs = s.execute(
        text(
            f"SELECT * FROM ({SELECT} WHERE {w}) x {nota_min} "
            "ORDER BY nota DESC, data_abertura DESC NULLS LAST, cnpj LIMIT :lim OFFSET :off"
        ),
        p,
    ).mappings()
    linhas = _marca([dict(r) for r in rs])
    if f.esconder_disparo:
        linhas = [r for r in linhas if not r["no_disparo"]][:POR_PAGINA]
    return linhas, int(total)


def para_planilha(
    s: Session, f: Filtros, cnpjs: list[str] | None = None
) -> list[dict[str, Any]]:
    w, p = _where(f, s)
    p |= _params_base(f)
    if cnpjs:
        w += " AND e.cnpj = ANY(:cnpjs)"
        p["cnpjs"] = [c.upper() for c in cnpjs]
    nota_min = f"WHERE nota >= {int(f.nota_min)}" if f.nota_min else ""
    rs = s.execute(
        text(
            f"SELECT * FROM ({SELECT} WHERE {w}) x {nota_min} "
            f"ORDER BY nota DESC, data_abertura DESC NULLS LAST LIMIT {LIMITE_PLANILHA}"
        ),
        p,
    ).mappings()
    return _marca([dict(r) for r in rs])


def ficha(s: Session, cnpj: str, oferta: str = "geral") -> dict[str, Any] | None:
    p = _params_base(Filtros(oferta=oferta)) | {"cnpj": cnpj.upper()}
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
            "empresas": r["empresas"],
        }
        for r in rs
    ]


def clientes(s: Session) -> list[dict[str, Any]]:
    rs = s.execute(
        text(
            """SELECT c.nome, c.ofertas, c.ativo, c.valor_cents, c.cnpj,
                      pc.cnae_descricao, pc.porte, pc.capital_social, pc.anos, pc.cidade, pc.uf,
                      pc.socios, pc.achou_na_receita
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
            "porte": texto.PORTES.get(r["porte"] or "00", "")
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
