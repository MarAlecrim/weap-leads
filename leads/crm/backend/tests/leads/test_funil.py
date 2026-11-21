"""Funil (kanban): etapas automáticas a partir do agente, permissões por perfil e mudança à mão."""

from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, delete, select

from app import crud
from app.core.config import settings
from app.funil import etapas, sincronia
from app.models import Negocio, NegocioHistorico, UserCreate, UserUpdate
from tests.utils.user import user_authentication_headers
from tests.utils.utils import random_email, random_lower_string

API = f"{settings.API_V1_STR}/funil"


@pytest.fixture()
def limpo(db: Session) -> Generator[None, None, None]:
    def apagar() -> None:
        db.execute(delete(Negocio).where(col(Negocio.chave).like("5599%")))
        db.commit()

    apagar()
    yield
    apagar()


def _linha(chave: str, **kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "chave": chave,
        "telefone": chave,
        "instancia": "Teste-1111",
        "nome_empresa": "Empresa " + chave[-2:],
        "status": None,
        "opt_out": False,
        "ia_pausada": False,
        "origem_agente": "prospeccao",
        "ultimo_contato_em": None,
        "ultima_resposta_em": None,
        "cnpj": None,
        "cidade": None,
        "nota": None,
        "origem": None,
        "fila_status": None,
    }
    base.update(kw)
    return base


def _negocio(db: Session, chave: str) -> Negocio:
    db.expire_all()
    n = db.exec(select(Negocio).where(Negocio.chave == chave)).one()
    return n


def test_etapa_do_agente() -> None:
    assert etapas.etapa_do_agente(None, False, "novo") == ("fila", None)
    assert etapas.etapa_do_agente(None, False, "pulado") is None
    assert etapas.etapa_do_agente("agendado", False, None) == ("reuniao", None)
    assert etapas.etapa_do_agente("respondeu", True, None) == (
        "perdido",
        "Pediu para não receber",
    )
    assert etapas.etapa_do_agente("bot", False, None)[0] == "perdido"  # type: ignore[index]


def test_pode_avancar() -> None:
    assert etapas.pode_avancar("contatado", "respondeu")
    assert not etapas.pode_avancar("interessado", "respondeu")
    assert not etapas.pode_avancar("ganho", "perdido")
    assert etapas.pode_avancar("reuniao", "perdido")
    assert not etapas.pode_avancar("proposta", "perdido")


@pytest.mark.usefixtures("limpo")
def test_sincronia_cria_e_so_avanca(db: Session) -> None:
    sincronia.aplicar(
        db,
        [
            _linha(
                "5599000000001",
                fila_status="novo",
                origem="receita",
                nota=88,
                cidade="Londrina",
            ),
            _linha("5599000000002", status="respondeu"),
            _linha("5599000000003", fila_status="pulado"),
        ],
    )
    a = _negocio(db, "5599000000001")
    assert (a.etapa, a.origem, a.nota, a.cidade) == ("fila", "receita", 88, "Londrina")
    assert _negocio(db, "5599000000002").etapa == "respondeu"
    assert (
        db.exec(select(Negocio).where(Negocio.chave == "5599000000003")).first() is None
    )

    # o disparo mandou e o lead respondeu
    sincronia.aplicar(
        db,
        [
            _linha(
                "5599000000001",
                status="respondeu",
                fila_status="enviado",
                origem="receita",
            )
        ],
    )
    a = _negocio(db, "5599000000001")
    assert a.etapa == "respondeu"
    hist = db.exec(
        select(NegocioHistorico).where(NegocioHistorico.negocio_id == a.id)
    ).all()
    assert [(h.de, h.para, h.autor) for h in hist] == [
        (None, "fila", "agente"),
        ("fila", "respondeu", "agente"),
    ]

    # alguém levou à mão para "proposta": o agente não volta nem perde o card
    a.etapa = "proposta"
    db.add(a)
    db.commit()
    sincronia.aplicar(db, [_linha("5599000000001", status="sem_interesse")])
    assert _negocio(db, "5599000000001").etapa == "proposta"

    # antes da proposta, "sem interesse" leva para perdido com o motivo
    sincronia.aplicar(db, [_linha("5599000000002", status="sem_interesse")])
    b = _negocio(db, "5599000000002")
    assert (b.etapa, b.perdido_motivo) == ("perdido", "Sem interesse")


@pytest.mark.usefixtures("limpo")
def test_responsavel_pelo_numero(db: Session) -> None:
    vend = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=random_email(),
            password=random_lower_string(),
            perfil="vendedor",
            numeros=["Teste-1111"],
        ),
    )
    sincronia.aplicar(db, [_linha("5599000000004", status="contatado")])
    assert _negocio(db, "5599000000004").responsavel_id == vend.id
    crud.update_user(session=db, db_user=vend, user_in=UserUpdate(numeros=[]))


def test_perfil_admin_e_superuser(db: Session) -> None:
    u = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=random_email(), password=random_lower_string(), perfil="admin"
        ),
    )
    assert u.is_superuser
    u = crud.update_user(session=db, db_user=u, user_in=UserUpdate(perfil="gestor"))
    assert not u.is_superuser and u.perfil == "gestor"


@pytest.mark.usefixtures("limpo")
def test_rotas_do_funil(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
) -> None:
    agora = datetime.now(timezone.utc)
    sincronia.aplicar(
        db,
        [
            _linha(
                "5599000000005",
                status="contatado",
                ultimo_contato_em=agora - timedelta(days=5),
            ),
            _linha("5599000000006", status="respondeu", instancia="Outro-2222"),
        ],
    )
    r = client.get(f"{API}/", headers=superuser_token_headers)
    assert r.status_code == 200
    colunas = {c["etapa"]: c for c in r.json()["colunas"]}
    assert list(colunas) == [e for e, _ in etapas.ETAPAS]
    card = next(c for c in colunas["contatado"]["cards"] if c["nome"] == "Empresa 05")
    assert card["dias_sem_resposta"] == 5 and card["numero"] == "1111"

    nid = card["id"]
    r = client.patch(
        f"{API}/{nid}", headers=superuser_token_headers, json={"etapa": "perdido"}
    )
    assert r.status_code == 422
    r = client.patch(
        f"{API}/{nid}",
        headers=superuser_token_headers,
        json={"etapa": "proposta", "servico": "site_pro"},
    )
    assert r.status_code == 200
    assert (r.json()["etapa"], r.json()["valor_cents"]) == ("proposta", 170_000)

    # vendedor só vê os leads dos seus números
    senha = random_lower_string()
    email = random_email()
    vend = crud.create_user(
        session=db,
        user_create=UserCreate(email=email, password=senha, numeros=["Teste-1111"]),
    )
    h = user_authentication_headers(client=client, email=email, password=senha)
    r = client.get(f"{API}/", headers=h)
    nomes = {c["nome"] for col_ in r.json()["colunas"] for c in col_["cards"]}
    assert "Empresa 05" in nomes and "Empresa 06" not in nomes
    outro = _negocio(db, "5599000000006")
    assert (
        client.patch(
            f"{API}/{outro.id}", headers=h, json={"valor_cents": 100}
        ).status_code
        == 404
    )
    crud.update_user(session=db, db_user=vend, user_in=UserUpdate(numeros=[]))

    r = client.get(f"{API}/opcoes", headers=superuser_token_headers)
    assert r.status_code == 200 and r.json()["motivos"]


@pytest.mark.usefixtures("limpo")
def test_ler_agente_de_verdade(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """Roda a consulta no banco do agente de teste (AGENTE_DB_URL_TESTE), se houver."""
    import os

    from sqlalchemy import create_engine, text

    from app.leads import repo

    url = os.environ.get("AGENTE_DB_URL_TESTE", "")
    if not url:
        pytest.skip("sem banco do agente de teste")
    eng = create_engine(url)
    with eng.begin() as c:
        c.execute(text("DELETE FROM sdr_leads WHERE chave LIKE '5599%'"))
        c.execute(text("DELETE FROM sdr_fila WHERE chave LIKE '5599%'"))
        c.execute(
            text(
                "INSERT INTO sdr_leads (chave, telefone, instancia, nome_empresa, status) "
                "VALUES ('5599000000007', '5599000000007', 'Teste-1111', 'Lead do agente', 'interessado')"
            )
        )
        c.execute(
            text(
                "INSERT INTO sdr_fila (chave, telefone, nome_empresa, nota, origem) "
                "VALUES ('5599000000008', '5599000000008', 'Lead da fila', 77, 'receita')"
            )
        )
    monkeypatch.setattr(settings, "AGENTE_DB_URL", url)
    repo._engine_agente.cache_clear()
    try:
        assert sincronia.sincronizar(db, forcar=True)
        assert _negocio(db, "5599000000007").etapa == "interessado"
        f = _negocio(db, "5599000000008")
        assert (f.etapa, f.nota, f.origem) == ("fila", 77, "receita")
    finally:
        repo._engine_agente.cache_clear()
        with eng.begin() as c:
            c.execute(text("DELETE FROM sdr_leads WHERE chave LIKE '5599%'"))
            c.execute(text("DELETE FROM sdr_fila WHERE chave LIKE '5599%'"))
