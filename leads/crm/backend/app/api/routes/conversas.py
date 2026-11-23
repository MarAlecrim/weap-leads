"""Caixa de conversas: lista as conversas de todos os números, abre, responde e pausa/retoma a IA."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import col, select

from app.api.deps import CurrentUser, SessionDep
from app.api.routes.funil import Mensagem, _numero, ve_tudo
from app.core.config import settings
from app.funil import conversas
from app.models import ConversaLida, Negocio, User

router = APIRouter(prefix="/conversas", tags=["conversas"])


class ConversaItem(BaseModel):
    chave: str
    nome: str
    instancia: str | None
    numero: str | None
    status: str | None
    ia_pausada: bool
    opt_out: bool
    ultima_texto: str | None
    ultima_autor: str
    ultima_em: datetime
    ultima_id: int
    nao_lidas: int
    negocio_id: int | None


class ListaConversas(BaseModel):
    conversas: list[ConversaItem]
    tem_mais: bool
    nao_lidas: int
    ligado_ao_agente: bool
    pode_responder: bool


class Conversa(BaseModel):
    chave: str
    nome: str
    instancia: str | None
    numero: str | None
    status: str | None
    ia_pausada: bool
    opt_out: bool
    resumo: str | None
    negocio_id: int | None
    mensagens: list[Mensagem]
    pode_responder: bool


class Resposta(BaseModel):
    texto: str = Field(min_length=1, max_length=4000)


def _pode_responder() -> bool:
    return bool(settings.EVOLUTION_API_KEY)


def _meus_leads(session: SessionDep, u: User) -> list[str]:
    """Chaves dos cards em que a pessoa é a responsável (além dos números dela)."""
    return [
        c
        for (c,) in session.execute(
            select(Negocio.chave).where(Negocio.responsavel_id == u.id)
        ).all()
    ]


def _lidas(session: SessionDep, u: User) -> dict[str, int]:
    return {
        r.chave: r.ate_id
        for r in session.exec(
            select(ConversaLida).where(ConversaLida.user_id == u.id)
        ).all()
    }


def _negocios(session: SessionDep, chaves: list[str]) -> dict[str, int]:
    if not chaves:
        return {}
    return {
        c: i
        for c, i in session.execute(
            select(Negocio.chave, Negocio.id).where(col(Negocio.chave).in_(chaves))
        ).all()
        if i is not None
    }


@router.get("/", response_model=ListaConversas)
def lista(
    session: SessionDep,
    u: CurrentUser,
    instancia: str | None = Query(default=None, max_length=120),
    nao_lidas: bool = False,
    busca: str = Query(default="", max_length=100),
    antes: int | None = None,
) -> Any:
    """Conversas da mais recente para a mais antiga. Vendedor vê só os números dele e os
    leads em que é o responsável."""
    todas = ve_tudo(u)
    try:
        r = conversas.listar(
            todas=todas,
            numeros=list(u.numeros or []),
            extra=[] if todas else _meus_leads(session, u),
            lidas=_lidas(session, u),
            instancia=instancia,
            so_nao_lidas=nao_lidas,
            busca=busca,
            antes=antes,
        )
    except Exception:
        conversas.log.exception("não consegui ler as conversas no banco do agente")
        raise HTTPException(
            status_code=503, detail="Não consegui ler as conversas agora."
        )
    if r is None:
        return ListaConversas(
            conversas=[],
            tem_mais=False,
            nao_lidas=0,
            ligado_ao_agente=False,
            pode_responder=False,
        )
    neg = _negocios(session, [c["chave"] for c in r["conversas"]])
    return ListaConversas(
        conversas=[
            ConversaItem(
                **{k: c[k] for k in ConversaItem.model_fields if k in c},
                numero=_numero(c["instancia"]),
                negocio_id=neg.get(c["chave"]),
            )
            for c in r["conversas"]
        ],
        tem_mais=r["tem_mais"],
        nao_lidas=r["nao_lidas"],
        ligado_ao_agente=True,
        pode_responder=_pode_responder(),
    )


def _lead_visivel(session: SessionDep, u: User, chave: str) -> dict[str, Any]:
    try:
        ld = conversas.lead(chave)
    except Exception:
        conversas.log.exception("não consegui ler o lead no banco do agente")
        raise HTTPException(
            status_code=503, detail="Não consegui ler a conversa agora."
        )
    if not ld:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    if not ve_tudo(u) and ld["instancia"] not in (u.numeros or []):
        dono = session.exec(
            select(Negocio.id).where(
                Negocio.chave == chave, Negocio.responsavel_id == u.id
            )
        ).first()
        if not dono:
            raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    return ld


def _marcar_lida(session: SessionDep, u: User, chave: str, ate: int) -> None:
    if not ate:
        return
    stmt = insert(ConversaLida).values(user_id=u.id, chave=chave, ate_id=ate)
    session.execute(
        stmt.on_conflict_do_update(
            index_elements=["user_id", "chave"],
            set_={"ate_id": stmt.excluded.ate_id},
            where=col(ConversaLida.ate_id) < stmt.excluded.ate_id,
        )
    )
    session.commit()


def _conversa(session: SessionDep, u: User, ld: dict[str, Any]) -> Conversa:
    msgs = conversas.mensagens(ld["id"])
    _marcar_lida(session, u, ld["chave"], max((m["id"] for m in msgs), default=0))
    return Conversa(
        chave=ld["chave"],
        nome=ld["nome"],
        instancia=ld["instancia"],
        numero=_numero(ld["instancia"]),
        status=ld["status"],
        ia_pausada=ld["ia_pausada"],
        opt_out=ld["opt_out"],
        resumo=ld["resumo"],
        negocio_id=_negocios(session, [ld["chave"]]).get(ld["chave"]),
        mensagens=[Mensagem(**m) for m in msgs],
        pode_responder=_pode_responder() and not ld["opt_out"],
    )


def _pausa_no_card(session: SessionDep, chave: str, pausada: bool) -> None:
    n = session.exec(select(Negocio).where(Negocio.chave == chave)).first()
    if n:
        n.ia_pausada = pausada
        if pausada:
            n.status_agente = (
                n.status_agente
                if n.status_agente in ("agendado", "sem_interesse", "bot")
                else "humano"
            )
        elif n.status_agente == "humano":
            n.status_agente = "respondeu"
        session.add(n)
        session.commit()


@router.get("/{chave}", response_model=Conversa)
def abrir(session: SessionDep, u: CurrentUser, chave: str) -> Any:
    """Mensagens do lead (as últimas 300) e o resumo da IA. Marca como lida."""
    return _conversa(session, u, _lead_visivel(session, u, chave))


@router.post("/{chave}/responder", response_model=Conversa)
def responder(session: SessionDep, u: CurrentUser, chave: str, r: Resposta) -> Any:
    """Manda a resposta pelo número que conversa com o lead e pausa a IA desse lead."""
    _lead_visivel(session, u, chave)
    try:
        conversas.responder(chave, r.texto.strip())
    except conversas.SemEvolution:
        raise HTTPException(
            status_code=503,
            detail="Responder pelo CRM ainda não está ligado (falta a Evolution no servidor).",
        )
    except conversas.NaoPodeEnviar as e:
        raise HTTPException(status_code=409, detail=str(e))
    except conversas.EvolutionFalhou as e:
        raise HTTPException(status_code=502, detail=str(e))
    _pausa_no_card(session, chave, True)
    return _conversa(session, u, _lead_visivel(session, u, chave))


@router.post("/{chave}/retomar", response_model=Conversa)
def retomar(session: SessionDep, u: CurrentUser, chave: str) -> Any:
    """A IA volta a responder esse lead."""
    _lead_visivel(session, u, chave)
    conversas.retomar(chave)
    _pausa_no_card(session, chave, False)
    return _conversa(session, u, _lead_visivel(session, u, chave))
