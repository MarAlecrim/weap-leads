"""Painel da tela inicial: funil, disparo por dia e por número, e o que precisa de atenção.

Quase tudo sai do banco do CRM (crm_negocio), que é pequeno e rápido. A série por dia e a fila
vêm do banco do agente; se ele estiver fora, o painel mostra o resto.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.api.routes.funil import Card, _card, _nomes, _numero, _visiveis, ve_tudo
from app.funil import etapas, sincronia
from app.leads import repo
from app.models import Negocio

router = APIRouter(prefix="/painel", tags=["painel"])

SP = ZoneInfo("America/Sao_Paulo")
DIAS_SERIE = 14
# Etapas que contam como "respondeu" (o lead escreveu de volta pelo menos uma vez)
RESPONDERAM = ["respondeu", "interessado", "reuniao", "proposta", "negociacao", "ganho"]
EM_ABERTO = ["proposta", "negociacao"]


class EtapaContagem(BaseModel):
    etapa: str
    nome: str
    total: int
    valor_cents: int


class Dia(BaseModel):
    dia: date
    enviados: int
    respostas: int


class PorNumero(BaseModel):
    instancia: str
    numero: str
    contatados: int
    responderam: int
    interessados: int


class Painel(BaseModel):
    na_fila: int | None
    enviados_hoje: int | None
    contatados: int
    responderam: int
    interessados: int
    reunioes: int
    abertos_valor_cents: int
    abertos: int
    ganhos: int
    ganhos_valor_cents: int
    clientes_atuais: int | None
    etapas: list[EtapaContagem]
    por_dia: list[Dia] | None
    por_numero: list[PorNumero]
    atencao: list[Card]
    atencao_total: int


def _serie(instancias: list[str] | None) -> list[Dia] | None:
    """Leads que receberam a 1ª mensagem do disparo e leads que responderam, por dia (Brasília)."""
    eng = repo._engine_agente()
    if not eng:
        return None
    hoje = datetime.now(SP).date()
    inicio = hoje - timedelta(days=DIAS_SERIE - 1)
    filtro = "" if instancias is None else "AND m.instancia = ANY(:inst)"
    sql = f"""
        SELECT (m.criado_em AT TIME ZONE 'America/Sao_Paulo')::date AS dia,
               count(DISTINCT m.lead_id) FILTER (WHERE m.autor = 'disparo') AS enviados,
               count(DISTINCT m.lead_id) FILTER (WHERE m.autor = 'lead') AS respostas
          FROM sdr_mensagens m
         WHERE m.criado_em >= (CAST(:inicio AS date) AT TIME ZONE 'America/Sao_Paulo')
           {filtro}
         GROUP BY 1"""
    try:
        with eng.connect() as c:
            linhas = {
                r.dia: r
                for r in c.execute(
                    text(sql), {"inicio": inicio, "inst": instancias or []}
                )
            }
    except Exception:
        return None
    return [
        Dia(
            dia=d,
            enviados=linhas[d].enviados if d in linhas else 0,
            respostas=linhas[d].respostas if d in linhas else 0,
        )
        for d in (inicio + timedelta(days=i) for i in range(DIAS_SERIE))
    ]


def _clientes(session: SessionDep) -> int | None:
    try:
        return int(
            session.execute(text("SELECT count(*) FROM receita.clientes_weap")).scalar()
            or 0
        )
    except Exception:
        session.rollback()
        return None


@router.get("/", response_model=Painel)
def painel(session: SessionDep, u: CurrentUser) -> Any:
    sincronia.sincronizar(session)
    negocios = session.exec(_visiveis(select(Negocio), u)).all()
    agora = datetime.now(timezone.utc)
    nomes = _nomes(session)
    por_etapa: dict[str, list[Negocio]] = {e: [] for e, _ in etapas.ETAPAS}
    for n in negocios:
        por_etapa.setdefault(n.etapa, []).append(n)

    def conta(es: list[str]) -> int:
        return sum(len(por_etapa[e]) for e in es)

    def soma(es: list[str]) -> int:
        return sum(n.valor_cents or 0 for e in es for n in por_etapa[e])

    # "Responderam" também conta quem respondeu e depois foi perdido
    perdidos_que_responderam = sum(
        1 for n in por_etapa["perdido"] if n.ultima_resposta_em
    )

    numeros: dict[str, dict[str, int]] = {}
    for n in negocios:
        if not n.instancia or n.etapa == "fila":
            continue
        d = numeros.setdefault(
            n.instancia, {"contatados": 0, "responderam": 0, "interessados": 0}
        )
        d["contatados"] += 1
        if n.etapa in RESPONDERAM or n.ultima_resposta_em:
            d["responderam"] += 1
        if n.etapa in ("interessado", "reuniao", "proposta", "negociacao", "ganho"):
            d["interessados"] += 1

    cards = [
        _card(n, nomes, agora)
        for n in negocios
        if n.etapa not in etapas.FECHADAS and n.etapa != "fila"
    ]

    def precisa(c: Card) -> bool:
        vencida = c.proxima_acao_em is not None and c.proxima_acao_em < agora
        sem_resp = (
            c.dias_sem_resposta or 0
        ) >= etapas.DIAS_ALERTA and c.etapa != "contatado"
        return vencida or sem_resp or c.ia_pausada

    atencao = sorted(
        (c for c in cards if precisa(c)),
        key=lambda c: (c.proxima_acao_em is None, -(c.dias_sem_resposta or 0)),
    )
    try:
        fila = repo.resumo_fila() if ve_tudo(u) else None
    except Exception:
        fila = None
    instancias = None if ve_tudo(u) else list(u.numeros or [])
    por_dia = _serie(instancias)

    return Painel(
        na_fila=fila["aguardando"] + fila["enviando"] if fila else None,
        # o disparo pela planilha não passa pela fila: a série do agente conta os dois
        enviados_hoje=por_dia[-1].enviados
        if por_dia
        else (fila["enviados_hoje"] if fila else None),
        contatados=len(negocios) - len(por_etapa["fila"]),
        responderam=conta(RESPONDERAM) + perdidos_que_responderam,
        interessados=conta(["interessado"]),
        reunioes=conta(["reuniao"]),
        abertos=conta(EM_ABERTO),
        abertos_valor_cents=soma(EM_ABERTO),
        ganhos=conta(["ganho"]),
        ganhos_valor_cents=soma(["ganho"]),
        clientes_atuais=_clientes(session),
        etapas=[
            EtapaContagem(
                etapa=e, nome=nome, total=len(por_etapa[e]), valor_cents=soma([e])
            )
            for e, nome in etapas.ETAPAS
        ],
        por_dia=por_dia,
        por_numero=sorted(
            [
                PorNumero(instancia=k, numero=_numero(k) or k, **v)
                for k, v in numeros.items()
            ],
            key=lambda p: -p.contatados,
        ),
        atencao=atencao[:8],
        atencao_total=len(atencao),
    )
