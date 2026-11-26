"""Tela de números (sdr_instancias). Os testes com banco usam AGENTE_DB_URL_TESTE (administrador)
e, se houver, AGENTE_DB_URL_TESTE_CRM (usuário leads_crm, para conferir as permissões)."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import settings
from app.leads import repo

URL = os.environ.get("AGENTE_DB_URL_TESTE", "")
URL_CRM = os.environ.get("AGENTE_DB_URL_TESTE_CRM", "")
API = f"{settings.API_V1_STR}/leads/numeros"


def _usa(monkeypatch: pytest.MonkeyPatch, url: str | None) -> None:
    monkeypatch.setattr(settings, "AGENTE_DB_URL", url)
    repo._engine_agente.cache_clear()


@pytest.fixture()
def agente(monkeypatch: pytest.MonkeyPatch):
    if not URL:
        pytest.skip("sem banco do agente de teste (AGENTE_DB_URL_TESTE)")
    eng = create_engine(URL)
    _usa(monkeypatch, URL)
    yield eng
    with eng.begin() as c:
        c.execute(text("DELETE FROM sdr_instancias WHERE instancia LIKE 'teste-%'"))
    repo._engine_agente.cache_clear()


def _dados(**kw: object) -> dict:
    return {
        "instancia": "teste-1",
        "numero": "41 98526-1094",
        "responsavel": "Márcio",
        "aviso": "(41) 99134-8881",
        "cidade": "São Paulo",
        "ativo": False,
        "ufs": ["sp", "SP"],
    } | kw


def test_so_administrador_muda(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    r = client.post(API, headers=normal_user_token_headers, json=_dados())
    assert r.status_code == 403


def test_validacao(client: TestClient, superuser_token_headers: dict[str, str]) -> None:
    h = superuser_token_headers
    assert client.post(API, headers=h, json=_dados(ufs=["XX"])).status_code == 422
    assert client.post(API, headers=h, json=_dados(aviso="123")).status_code == 422
    assert client.post(API, headers=h, json=_dados(aviso="")).status_code == 422
    assert client.post(API, headers=h, json=_dados(instancia=" ")).status_code == 422


def test_sem_banco_do_agente(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _usa(monkeypatch, None)
    r = client.post(API, headers=superuser_token_headers, json=_dados())
    assert r.status_code == 503


def test_cadastra_e_altera(
    agente, client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    h = superuser_token_headers
    assert client.post(API, headers=h, json=_dados()).status_code == 201
    assert client.post(API, headers=h, json=_dados()).status_code == 409
    n = next(
        x for x in client.get(API, headers=h).json() if x["instancia"] == "teste-1"
    )
    assert n["numero"] == "5541985261094"
    assert n["aviso"] == "5541991348881"
    assert n["ufs"] == ["SP"] and n["ativo"] is False

    r = client.put(f"{API}/teste-1", headers=h, json=_dados(ufs=[], ativo=True))
    assert r.status_code == 200
    n = next(
        x for x in client.get(API, headers=h).json() if x["instancia"] == "teste-1"
    )
    assert n["ufs"] == [] and n["ativo"] is True
    with agente.connect() as c:
        assert (
            c.execute(
                text("SELECT ufs FROM sdr_instancias WHERE instancia = 'teste-1'")
            ).scalar()
            is None
        )
    assert (
        client.put(f"{API}/teste-nao-existe", headers=h, json=_dados()).status_code
        == 404
    )


@pytest.mark.usefixtures("agente")
def test_usuario_do_crm_tem_permissao(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if not URL_CRM:
        pytest.skip("sem AGENTE_DB_URL_TESTE_CRM")
    _usa(monkeypatch, URL_CRM)
    h = superuser_token_headers
    r = client.post(API, headers=h, json=_dados(instancia="teste-2"))
    assert r.status_code in (201, 409), r.text
    if r.status_code == 409:
        assert "SQL" in r.json()["detail"]
        return
    assert client.put(f"{API}/teste-2", headers=h, json=_dados()).status_code == 200
