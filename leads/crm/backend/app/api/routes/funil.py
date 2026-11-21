"""Funil (kanban): os cards dos leads do disparo, por etapa."""

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlmodel import col, select
from sqlmodel.sql.expression import SelectOfScalar

from app.api.deps import CurrentUser, SessionDep
from app.funil import etapas, sincronia
from app.leads import repo
from app.models import Negocio, NegocioHistorico, User

router = APIRouter(prefix="/funil", tags=["funil"])

POR_COLUNA = 100


class Card(BaseModel):
    id: int
    nome: str
    cnpj: str | None
    cidade: str | None
    origem: str
    nota: int | None
    instancia: str | None
    numero: str | None
    responsavel_id: uuid.UUID | None
    responsavel: str | None
    etapa: str
    valor_cents: int | None
    servico: str | None
    dias_na_etapa: int
    dias_sem_resposta: int | None
    ia_pausada: bool
    proxima_acao: str | None
    proxima_acao_em: datetime | None
    perdido_motivo: str | None


class Coluna(BaseModel):
    etapa: str
    nome: str
    total: int
    valor_cents: int
    cards: list[Card]


class Funil(BaseModel):
    colunas: list[Coluna]
    ligado_ao_agente: bool


class Item(BaseModel):
    id: str
    nome: str


class Servico(Item):
    valor_cents: int


class FunilOpcoes(BaseModel):
    etapas: list[Item]
    servicos: list[Servico]
    motivos: list[str]
    responsaveis: list[Item]
    numeros: list[Item]


class NegocioAtualiza(BaseModel):
    etapa: str | None = None
    valor_cents: int | None = None
    servico: str | None = None
    responsavel_id: uuid.UUID | None = None
    perdido_motivo: str | None = None
    proxima_acao: str | None = None
    proxima_acao_em: datetime | None = None


def ve_tudo(u: User) -> bool:
    return u.is_superuser or u.perfil in ("admin", "gestor")


def _visiveis(stmt: SelectOfScalar[Negocio], u: User) -> SelectOfScalar[Negocio]:
    if ve_tudo(u):
        return stmt
    return stmt.where(
        or_(
            col(Negocio.responsavel_id) == u.id,
            col(Negocio.instancia).in_(u.numeros or [""]),
        )
    )


def _numero(instancia: str | None) -> str | None:
    if not instancia:
        return None
    m = re.search(r"(\d{4})\D*$", instancia)
    return m.group(1) if m else instancia


def _dias(desde: datetime | None, agora: datetime) -> int | None:
    if not desde:
        return None
    return max(0, (agora - desde).days)


def _card(n: Negocio, nomes: dict[Any, str], agora: datetime) -> Card:
    sem_resposta = None
    if n.etapa not in etapas.FECHADAS and n.etapa != "fila" and n.ultimo_contato_em:
        if not n.ultima_resposta_em or n.ultima_resposta_em < n.ultimo_contato_em:
            sem_resposta = _dias(n.ultimo_contato_em, agora)
    return Card(
        id=n.id or 0,
        nome=n.nome,
        cnpj=n.cnpj,
        cidade=n.cidade,
        origem=n.origem,
        nota=n.nota,
        instancia=n.instancia,
        numero=_numero(n.instancia),
        responsavel_id=n.responsavel_id,
        responsavel=nomes.get(n.responsavel_id),
        etapa=n.etapa,
        valor_cents=n.valor_cents,
        servico=n.servico,
        dias_na_etapa=_dias(n.etapa_desde, agora) or 0,
        dias_sem_resposta=sem_resposta,
        ia_pausada=n.ia_pausada,
        proxima_acao=n.proxima_acao,
        proxima_acao_em=n.proxima_acao_em,
        perdido_motivo=n.perdido_motivo,
    )


def _nomes(session: SessionDep) -> dict[Any, str]:
    return {
        u.id: (u.full_name or u.email.split("@")[0])
        for u in session.exec(select(User)).all()
    }


@router.get("/opcoes", response_model=FunilOpcoes)
def opcoes(session: SessionDep, _u: CurrentUser) -> Any:
    numeros: dict[str, str] = {}
    eng = repo._engine_agente()
    if eng:
        try:
            from sqlalchemy import text

            with eng.connect() as c:
                for r in c.execute(
                    text(
                        "SELECT instancia, responsavel_nome FROM sdr_instancias ORDER BY instancia"
                    )
                ):
                    numeros[r.instancia] = (
                        f"{_numero(r.instancia)} · {r.responsavel_nome}"
                    )
        except Exception:
            pass
    for (inst,) in session.execute(select(Negocio.instancia).distinct()).all():
        if inst and inst not in numeros:
            numeros[inst] = _numero(inst) or inst
    users = session.exec(select(User).where(User.is_active)).all()
    return FunilOpcoes(
        etapas=[Item(id=e, nome=n) for e, n in etapas.ETAPAS],
        servicos=[Servico(id=s, nome=n, valor_cents=v) for s, n, v in etapas.SERVICOS],
        motivos=etapas.MOTIVOS_PERDA,
        responsaveis=sorted(
            [
                Item(id=str(u.id), nome=u.full_name or u.email.split("@")[0])
                for u in users
            ],
            key=lambda i: i.nome,
        ),
        numeros=[Item(id=k, nome=v) for k, v in numeros.items()],
    )


@router.get("/", response_model=Funil)
def funil(
    session: SessionDep,
    u: CurrentUser,
    responsavel_id: uuid.UUID | None = None,
    instancia: str | None = None,
    origem: str | None = None,
    parados: bool = False,
    busca: str = Query(default="", max_length=100),
) -> Any:
    sincronia.sincronizar(session)
    stmt = _visiveis(select(Negocio), u)
    if responsavel_id:
        stmt = stmt.where(Negocio.responsavel_id == responsavel_id)
    if instancia:
        stmt = stmt.where(Negocio.instancia == instancia)
    if origem:
        stmt = stmt.where(Negocio.origem == origem)
    if busca.strip():
        b = busca.strip()
        digitos = re.sub(r"\D", "", b)
        conds = [col(Negocio.nome).ilike(f"%{b}%")]
        if len(digitos) >= 4:
            conds += [
                col(Negocio.cnpj).like(f"%{digitos}%"),
                col(Negocio.chave).like(f"%{digitos}%"),
            ]
        stmt = stmt.where(or_(*conds))
    agora = datetime.now(timezone.utc)
    nomes = _nomes(session)
    cards = [_card(n, nomes, agora) for n in session.exec(stmt).all()]
    if parados:
        cards = [
            c
            for c in cards
            if c.etapa not in etapas.FECHADAS
            and (
                c.dias_na_etapa >= etapas.DIAS_ALERTA
                or (c.dias_sem_resposta or 0) >= etapas.DIAS_ALERTA
            )
        ]
    colunas = []
    for e, nome in etapas.ETAPAS:
        da = [c for c in cards if c.etapa == e]
        da.sort(key=lambda c: (-(c.nota or 0), -c.dias_na_etapa))
        colunas.append(
            Coluna(
                etapa=e,
                nome=nome,
                total=len(da),
                valor_cents=sum(c.valor_cents or 0 for c in da),
                cards=da[:POR_COLUNA],
            )
        )
    return Funil(colunas=colunas, ligado_ao_agente=repo._engine_agente() is not None)


@router.patch("/{negocio_id}", response_model=Card)
def atualizar(
    session: SessionDep, u: CurrentUser, negocio_id: int, dados: NegocioAtualiza
) -> Any:
    n = session.exec(
        _visiveis(select(Negocio).where(Negocio.id == negocio_id), u)
    ).first()
    if not n:
        raise HTTPException(status_code=404, detail="Card não encontrado.")
    d = dados.model_dump(exclude_unset=True)
    agora = datetime.now(timezone.utc)
    if "etapa" in d and d["etapa"] is not None and d["etapa"] != n.etapa:
        nova = d["etapa"]
        if nova not in etapas.NOMES:
            raise HTTPException(status_code=422, detail="Etapa inválida.")
        if nova == "perdido" and not (d.get("perdido_motivo") or n.perdido_motivo):
            raise HTTPException(status_code=422, detail="Escolha o motivo da perda.")
        session.add(
            NegocioHistorico(
                negocio_id=n.id, de=n.etapa, para=nova, autor=u.full_name or u.email
            )
        )
        n.etapa, n.etapa_desde, n.movido_manual = nova, agora, True
        if nova != "perdido":
            n.perdido_motivo = None
    if "servico" in d:
        if d["servico"] and d["servico"] not in etapas.VALOR_SERVICO:
            raise HTTPException(status_code=422, detail="Serviço inválido.")
        n.servico = d["servico"]
        if d["servico"] and "valor_cents" not in d and not n.valor_cents:
            n.valor_cents = etapas.VALOR_SERVICO[d["servico"]] or None
    if "valor_cents" in d:
        if d["valor_cents"] is not None and d["valor_cents"] < 0:
            raise HTTPException(status_code=422, detail="Valor inválido.")
        n.valor_cents = d["valor_cents"]
    if "responsavel_id" in d:
        if d["responsavel_id"] and not session.get(User, d["responsavel_id"]):
            raise HTTPException(status_code=422, detail="Responsável não encontrado.")
        n.responsavel_id = d["responsavel_id"]
    if "perdido_motivo" in d and n.etapa == "perdido":
        n.perdido_motivo = d["perdido_motivo"] or n.perdido_motivo
    for campo in ("proxima_acao", "proxima_acao_em"):
        if campo in d:
            setattr(n, campo, d[campo])
    n.atualizado_em = agora
    session.add(n)
    session.commit()
    session.refresh(n)
    return _card(n, _nomes(session), agora)
