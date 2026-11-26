import csv
import io
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
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
    # só no "Mandar para o disparo": números que vão disparar esta lista (vazio = por estado)
    instancias: list[str] = []


class Numero(BaseModel):
    instancia: str
    numero: str
    responsavel: str
    aviso: str = ""
    cidade: str = ""
    ativo: bool
    ufs: list[str]


class NumeroDados(BaseModel):
    """Cadastro de um número pela tela do Admin."""

    instancia: str
    numero: str = ""
    responsavel: str
    aviso: str
    cidade: str = ""
    ativo: bool = True
    ufs: list[str] = []


def _fone(v: str, campo: str) -> str:
    d = "".join(ch for ch in v if ch.isdigit())
    if not d:
        return ""
    if len(d) in (10, 11):
        d = "55" + d
    if not (d.startswith("55") and len(d) in (12, 13)):
        raise HTTPException(
            status_code=422, detail=f"{campo}: use DDD + número, ex.: 41 99134-8881"
        )
    return d


def _limpa_numero(n: NumeroDados) -> dict[str, Any]:
    ufs = list(dict.fromkeys(u.strip().upper() for u in n.ufs if u.strip()))
    if bad := [u for u in ufs if u not in texto.UFS]:
        raise HTTPException(
            status_code=422, detail=f"Estado inválido: {', '.join(bad)}"
        )
    instancia = n.instancia.strip()
    if not instancia:
        raise HTTPException(status_code=422, detail="Informe o nome da instância")
    aviso = _fone(n.aviso, "Celular de aviso")
    if not aviso:
        raise HTTPException(status_code=422, detail="Informe o celular de aviso")
    if not n.responsavel.strip():
        raise HTTPException(status_code=422, detail="Informe o responsável")
    return {
        "instancia": instancia,
        "numero": _fone(n.numero, "Número"),
        "responsavel": n.responsavel.strip(),
        "aviso": aviso,
        "cidade": n.cidade.strip(),
        "ativo": n.ativo,
        "ufs": ufs,
    }


def _salva(dados: dict[str, Any], novo: bool) -> None:
    try:
        ok = repo.salvar_numero(dados, novo)
    except repo.SemBancoDoAgente:
        raise HTTPException(
            status_code=503, detail="O CRM ainda não está ligado ao banco do disparo."
        )
    except repo.SemPermissaoNosNumeros:
        raise HTTPException(
            status_code=409,
            detail="O banco do disparo ainda não deixa o CRM mudar os números (falta o SQL da tela de números).",
        )
    except repo.NumeroJaExiste:
        raise HTTPException(
            status_code=409, detail="Já existe um número com essa instância."
        )
    if not ok:
        raise HTTPException(status_code=404, detail="Número não encontrado")


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


@router.get("/numeros", response_model=list[Numero] | None)
def numeros(_u: CurrentUser) -> Any:
    """Números de WhatsApp do disparo, com os estados de cada um (vazio se o banco do agente não estiver ligado)."""
    r = repo.numeros()
    return [Numero(**n) for n in r] if r is not None else None


@router.post(
    "/numeros",
    status_code=201,
    dependencies=[Depends(get_current_active_superuser)],
)
def criar_numero(dados: NumeroDados) -> None:
    """Cadastra um número de WhatsApp do disparo (só administrador)."""
    _salva(_limpa_numero(dados), novo=True)


@router.put(
    "/numeros/{instancia}",
    dependencies=[Depends(get_current_active_superuser)],
)
def alterar_numero(instancia: str, dados: NumeroDados) -> None:
    """Muda estados, responsável, celular de aviso e ligado/desligado de um número (só administrador)."""
    d = _limpa_numero(dados.model_copy(update={"instancia": instancia}))
    _salva(d, novo=False)


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
        return FilaResultado(
            **repo.mandar_para_fila(linhas, u.email, pedido.instancias)
        )
    except repo.SemBancoDoAgente:
        raise HTTPException(
            status_code=503, detail="O CRM ainda não está ligado ao banco do disparo."
        )
    except repo.SemEscolhaDeNumeros:
        raise HTTPException(
            status_code=409,
            detail="O banco do disparo ainda não aceita escolher os números. Mande no automático.",
        )
    except repo.NumeroDesconhecido as e:
        raise HTTPException(status_code=422, detail=f"Número desconhecido: {e}")


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
