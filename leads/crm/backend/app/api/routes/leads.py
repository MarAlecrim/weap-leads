import csv
import io
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import CurrentUser, SessionDep
from app.leads import repo, texto

router = APIRouter(prefix="/leads", tags=["leads"])


class Socio(BaseModel):
    nome: str
    pessoa_fisica: bool
    qualificacao: str
    desde: str | None
    administra: bool


class Lead(BaseModel):
    cnpj: str
    nome: str
    razao_social: str
    atividade: str
    cnae: str | None
    porte: str
    simples: bool
    capital_social: float
    anos: int | None
    bairro: str
    cidade: str
    uf: str | None
    endereco: str
    telefone1: str
    telefone2: str
    whatsapp: str
    email: str
    decisor: str
    n_socios: int
    nota: int
    motivos: list[str]
    no_disparo: bool


class LeadFicha(Lead):
    socios: list[Socio]


class LeadsPagina(BaseModel):
    data: list[Lead]
    count: int
    pagina: int
    por_pagina: int


class Opcao(BaseModel):
    id: str
    nome: str


class Cidade(Opcao):
    uf: str | None = None
    empresas: int


class Perfil(Opcao):
    clientes: int


class Opcoes(BaseModel):
    nichos: list[Opcao]
    ufs: list[Opcao]
    cidades: list[Cidade]
    portes: list[Opcao]
    ofertas: list[Perfil]
    pesos: dict[str, int]
    motivos: dict[str, str]


class Cliente(BaseModel):
    nome: str
    ofertas: list[str]
    ativo: bool
    valor: float
    cnpj: str | None
    atividade: str
    porte: str
    anos: int | None
    cidade: str
    socios: int
    achou: bool


class PlanilhaPedido(BaseModel):
    filtros: dict[str, Any] = {}
    cnpjs: list[str] = []
    pular_disparo: bool = True


class FilaResumo(BaseModel):
    aguardando: int
    enviando: int
    enviados_hoje: int
    enviados: int
    pulados: int


class FilaResultado(BaseModel):
    adicionados: int
    ja_no_disparo: int
    sem_whatsapp: int


def _linhas_do_pedido(
    session: SessionDep, pedido: PlanilhaPedido
) -> list[dict[str, Any]]:
    q = {k: v for k, v in pedido.filtros.items() if v not in (None, "")}
    if "porte" in q and isinstance(q["porte"], str):
        q["porte"] = [q["porte"]]
    q.pop("pagina", None)
    try:
        f = _filtros(**q)
    except TypeError:
        raise HTTPException(status_code=422, detail="Filtro inválido")
    return repo.para_planilha(session, f, pedido.cnpjs or None)


def _filtros(
    oferta: str = "geral",
    nicho: str = "",
    secundario: bool = False,
    cidade: str = "",
    bairro: str = "",
    nome: str = "",
    porte: list[str] | None = None,
    capital_min: float | None = None,
    capital_max: float | None = None,
    anos_min: int | None = None,
    anos_max: int | None = None,
    celular: bool = True,
    email: bool = False,
    socio: bool = False,
    nota_min: int | None = None,
    esconder_disparo: bool = False,
    uf: str = "",
) -> repo.Filtros:
    return repo.Filtros(
        oferta=oferta,
        nicho=nicho.strip(),
        secundario=secundario,
        cidade=cidade.strip(),
        bairro=bairro.strip(),
        nome=nome.strip(),
        porte=porte or [],
        capital_min=capital_min,
        capital_max=capital_max,
        anos_min=anos_min,
        anos_max=anos_max,
        celular=celular,
        email=email,
        socio=socio,
        nota_min=nota_min,
        esconder_disparo=esconder_disparo,
        uf=uf.strip().upper(),
    )


@router.get("/opcoes", response_model=Opcoes)
def opcoes(session: SessionDep, _u: CurrentUser) -> Any:
    """Listas para os filtros da busca."""
    return Opcoes(
        nichos=[Opcao(**n) for n in repo.nichos(session)],
        ufs=[Opcao(**u) for u in repo.ufs(session)],
        cidades=[Cidade(**c) for c in repo.cidades(session)],
        portes=[Opcao(id=k, nome=v) for k, v in texto.FAIXAS.items()],
        ofertas=[Perfil(**p) for p in repo.perfis(session)],
        pesos=repo.PESOS,
        motivos=repo.MOTIVOS,
    )


@router.get("/", response_model=LeadsPagina)
def buscar(
    session: SessionDep,
    _u: CurrentUser,
    oferta: str = "geral",
    nicho: str = "",
    secundario: bool = False,
    cidade: str = "",
    bairro: str = "",
    nome: str = "",
    porte: Annotated[list[str] | None, Query()] = None,
    capital_min: float | None = None,
    capital_max: float | None = None,
    anos_min: int | None = None,
    anos_max: int | None = None,
    celular: bool = True,
    email: bool = False,
    socio: bool = False,
    nota_min: int | None = None,
    esconder_disparo: bool = False,
    uf: str = "",
    pagina: int = 1,
) -> Any:
    """Busca na base da Receita, da nota mais alta para a mais baixa."""
    f = _filtros(
        oferta,
        nicho,
        secundario,
        cidade,
        bairro,
        nome,
        porte,
        capital_min,
        capital_max,
        anos_min,
        anos_max,
        celular,
        email,
        socio,
        nota_min,
        esconder_disparo,
        uf=uf,
    )
    linhas, total = repo.buscar(session, f, pagina)
    return LeadsPagina(
        data=[Lead(**r) for r in linhas],
        count=total,
        pagina=pagina,
        por_pagina=repo.POR_PAGINA,
    )


@router.get("/clientes", response_model=list[Cliente])
def clientes(session: SessionDep, _u: CurrentUser) -> Any:
    """Clientes atuais da Weap e o perfil deles na Receita (base da nota)."""
    return [Cliente(**c) for c in repo.clientes(session)]


@router.get("/fila", response_model=FilaResumo | None)
def fila(_u: CurrentUser) -> Any:
    """Situação da fila do disparo no banco do agente (vazio se não estiver ligado)."""
    r = repo.resumo_fila()
    return FilaResumo(**r) if r else None


@router.get("/{cnpj}", response_model=LeadFicha)
def ficha(
    session: SessionDep, _u: CurrentUser, cnpj: str, oferta: str = "geral"
) -> Any:
    """Ficha da empresa com sócios e decisor."""
    r = repo.ficha(session, "".join(ch for ch in cnpj if ch.isalnum()), oferta)
    if not r:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return LeadFicha(**r)


@router.post("/disparo", response_model=FilaResultado)
def mandar_para_disparo(
    session: SessionDep, u: CurrentUser, pedido: PlanilhaPedido
) -> Any:
    """Coloca os leads (marcados ou do filtro, até 3.000) na fila do disparo do n8n."""
    linhas = _linhas_do_pedido(session, pedido)
    try:
        return FilaResultado(**repo.mandar_para_fila(linhas, u.email))
    except repo.SemBancoDoAgente:
        raise HTTPException(
            status_code=503, detail="O CRM ainda não está ligado ao banco do disparo."
        )


@router.post("/planilha")
def planilha(
    session: SessionDep, _u: CurrentUser, pedido: PlanilhaPedido
) -> StreamingResponse:
    """CSV no mesmo formato da planilha do disparo (só quem tem celular)."""
    linhas = _linhas_do_pedido(session, pedido)
    if pedido.pular_disparo:
        linhas = [r for r in linhas if not r["no_disparo"]]
    linhas = [r for r in linhas if r["whatsapp"]]

    buf = io.StringIO()
    buf.write("﻿")  # acentos certos no Excel e no Google Planilhas
    w = csv.writer(buf)
    w.writerow(
        [
            "nome_empresa",
            "telefone",
            "endereco",
            "website",
            "rating",
            "reviews",
            "especialidades",
            "mensagem",
            "disparo",
            "decisor",
            "email",
            "cnpj",
            "nota",
        ]
    )
    for r in linhas:
        w.writerow(
            [
                r["nome"],
                f"55{r['whatsapp']}@s.whatsapp.net",
                r["endereco"],
                "",
                "",
                "",
                r["atividade"],
                "",
                "",
                r["decisor"],
                r["email"],
                r["cnpj"],
                r["nota"],
            ]
        )
    nome = f"leads-{pedido.filtros.get('nicho') or 'busca'}-{datetime.now():%Y-%m-%d-%H%M}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )
