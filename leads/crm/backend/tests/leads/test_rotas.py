"""Rotas da busca. Precisa do banco com o schema receita (banco/01 a 05 do leads/)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session

from app.core.config import settings


@pytest.fixture(scope="module", autouse=True)
def precisa_da_receita(db: Session) -> None:
    ok = db.execute(
        text("SELECT to_regclass('receita.perfil_oferta') IS NOT NULL")
    ).scalar()
    if not ok:
        pytest.skip("banco sem o schema receita")


def test_busca_pede_login(client: TestClient) -> None:
    assert client.get(f"{settings.API_V1_STR}/leads/").status_code == 401


def test_busca_ordenada_pela_nota(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.get(f"{settings.API_V1_STR}/leads/", headers=superuser_token_headers)
    assert r.status_code == 200
    notas = [x["nota"] for x in r.json()["data"]]
    assert notas == sorted(notas, reverse=True)
    assert all(0 <= n <= 100 for n in notas)


def test_opcoes(client: TestClient, superuser_token_headers: dict[str, str]) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/leads/opcoes", headers=superuser_token_headers
    )
    assert r.status_code == 200
    assert sum(r.json()["pesos"].values()) == 100


def test_ficha_inexistente(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/leads/00000000000000", headers=superuser_token_headers
    )
    assert r.status_code == 404
