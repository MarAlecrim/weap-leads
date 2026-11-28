"""Nichos da busca (receita.nicho_cnaes) pela tela do Admin."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session

from app.core.config import settings

API = f"{settings.API_V1_STR}/leads/nichos"


@pytest.fixture()
def cnaes(db: Session) -> list[str]:
    if not db.execute(text("SELECT to_regclass('receita.cnaes') IS NOT NULL")).scalar():
        pytest.skip("banco sem o schema receita")
    cs = [r[0] for r in db.execute(text("SELECT codigo FROM receita.cnaes LIMIT 2"))]
    if len(cs) < 2:
        pytest.skip("receita.cnaes com menos de 2 atividades")
    yield cs
    db.execute(text("DELETE FROM receita.nicho_cnaes WHERE nicho LIKE 'teste %'"))
    db.commit()


def test_so_administrador(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    h = normal_user_token_headers
    assert client.get(API, headers=h).status_code == 403
    r = client.post(API, headers=h, json={"nome": "x", "cnaes": ["4781400"]})
    assert r.status_code == 403


def test_cria_edita_e_apaga(
    client: TestClient, superuser_token_headers: dict[str, str], cnaes: list[str]
) -> None:
    h = superuser_token_headers
    a, b = cnaes
    fmt = f"{a[:4]}-{a[4]}/{a[5:]}"
    r = client.post(API, headers=h, json={"nome": "  Teste   Padaria ", "cnaes": [fmt]})
    assert r.status_code == 201, r.text
    assert r.json() == "teste padaria"
    # aparece na lista da busca e filtra
    op = client.get(f"{settings.API_V1_STR}/leads/opcoes", headers=h).json()
    assert {"id": "teste padaria", "nome": "Teste padaria"} in op["nichos"]
    lista = {n["id"]: n for n in client.get(API, headers=h).json()}
    assert [c["id"] for c in lista["teste padaria"]["cnaes"]] == [a]
    # mesmo nome de novo: recusa
    r = client.post(API, headers=h, json={"nome": "teste padaria", "cnaes": [a]})
    assert r.status_code == 422
    # renomeia e troca as atividades
    r = client.put(
        f"{API}/teste padaria", headers=h, json={"nome": "Teste Pães", "cnaes": [a, b]}
    )
    assert r.status_code == 200, r.text
    lista = {n["id"]: n for n in client.get(API, headers=h).json()}
    assert "teste padaria" not in lista
    assert {c["id"] for c in lista["teste pães"]["cnaes"]} == {a, b}
    assert client.delete(f"{API}/teste pães", headers=h).status_code == 204
    assert client.delete(f"{API}/teste pães", headers=h).status_code == 404


def test_recusa_sem_atividade_ou_atividade_inexistente(
    client: TestClient, superuser_token_headers: dict[str, str], cnaes: list[str]
) -> None:
    h = superuser_token_headers
    assert (
        client.post(API, headers=h, json={"nome": "teste a", "cnaes": []}).status_code
        == 422
    )
    r = client.post(API, headers=h, json={"nome": "teste b", "cnaes": ["0000000"]})
    assert r.status_code == 422
    assert "0000-0/00" in r.json()["detail"]
    assert (
        client.post(API, headers=h, json={"nome": " ", "cnaes": cnaes}).status_code
        == 422
    )


def test_editar_sem_trocar_o_nome_mantem_o_nicho(
    client: TestClient, superuser_token_headers: dict[str, str], cnaes: list[str]
) -> None:
    h = superuser_token_headers
    client.post(API, headers=h, json={"nome": "teste saude", "cnaes": [cnaes[0]]})
    nome = {n["id"]: n["nome"] for n in client.get(API, headers=h).json()}[
        "teste saude"
    ]
    r = client.put(f"{API}/teste saude", headers=h, json={"nome": nome, "cnaes": cnaes})
    assert r.json() == "teste saude"
