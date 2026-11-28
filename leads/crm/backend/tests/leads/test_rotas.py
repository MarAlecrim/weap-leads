"""Rotas da busca. Precisa do banco com o schema receita (banco/01 a 05 do leads/)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session

from app.core.config import settings
from app.leads import notas, repo


@pytest.fixture(scope="module", autouse=True)
def precisa_da_receita(db: Session) -> None:
    ok = db.execute(
        text("SELECT to_regclass('receita.perfil_oferta') IS NOT NULL")
    ).scalar()
    if not ok:
        pytest.skip("banco sem o schema receita")
    # deixa a tabela de notas pronta antes (senão a 1ª busca a refaz em segundo plano)
    assert notas.recalcular()
    notas._estado["checado"] = 0.0


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


def _busca(client: TestClient, h: dict[str, str], **params: object) -> dict:
    r = client.get(
        f"{settings.API_V1_STR}/leads/",
        headers=h,
        params={"celular": False, **params},
    )
    assert r.status_code == 200
    return r.json()


def test_filtro_de_porte(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    todos = _busca(client, superuser_token_headers)["count"]
    soma = 0
    for faixa, nome in [
        ("mei", "MEI"),
        ("me", "Microempresa"),
        ("epp", "Pequeno porte"),
        ("media", "Média"),
        ("grande", "Grande"),
    ]:
        j = _busca(client, superuser_token_headers, porte=faixa)
        soma += j["count"]
        assert all(x["porte"] == nome for x in j["data"])
    # as cinco faixas cobrem a base sem repetir ninguém (fora quem não tem porte informado)
    assert soma <= todos
    dois = _busca(client, superuser_token_headers, porte=["mei", "grande"])["count"]
    assert (
        dois
        == _busca(client, superuser_token_headers, porte="mei")["count"]
        + _busca(client, superuser_token_headers, porte="grande")["count"]
    )


def test_filtro_de_capital(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    j = _busca(client, superuser_token_headers, capital_min=10000, capital_max=500000)
    assert all(10000 <= x["capital_social"] <= 500000 for x in j["data"])
    nada = _busca(client, superuser_token_headers, capital_min=10, capital_max=1)
    assert nada["count"] == 0


@pytest.mark.parametrize(
    "filtros",
    [
        repo.Filtros(),
        repo.Filtros(celular=False),
        repo.Filtros(celular=False, nota_min=60),
        repo.Filtros(oferta="site", celular=False),
        repo.Filtros(celular=False, porte=["me", "mei"]),
        repo.Filtros(oferta="inexistente", email=True, celular=False),
        repo.Filtros(celular=False, uf="PR"),
    ],
)
def test_nota_guardada_igual_a_calculada(
    db: Session, monkeypatch: pytest.MonkeyPatch, filtros: repo.Filtros
) -> None:
    rapida, total_rapida = repo.buscar(db, filtros)
    assert notas.coluna(db, repo._oferta(filtros)) is not None
    monkeypatch.setattr(notas, "coluna", lambda *_: None)
    lenta, total_lenta = repo.buscar(db, filtros)
    assert total_rapida == total_lenta
    assert [(x["cnpj"], x["nota"], x["motivos"]) for x in rapida] == [
        (x["cnpj"], x["nota"], x["motivos"]) for x in lenta
    ]


def test_notas_refeitas_quando_clientes_mudam(db: Session) -> None:
    marca = notas._marca(db)
    db.execute(text("UPDATE receita.clientes_weap SET ofertas = ofertas || '{teste}'"))
    try:
        assert notas._marca(db) != marca
        assert not notas._em_dia(db)
    finally:
        db.rollback()
    assert notas._em_dia(db)


def test_filtro_de_estado(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    h = superuser_token_headers
    ufs = client.get(f"{settings.API_V1_STR}/leads/opcoes", headers=h).json()["ufs"]
    todos = _busca(client, h)["count"]
    soma = 0
    for u in ufs:
        j = _busca(client, h, uf=u["id"])
        soma += j["count"]
        assert all(x["uf"] == u["id"] for x in j["data"])
    assert soma == todos
    # minúsculo também vale
    if ufs:
        assert (
            _busca(client, h, uf=ufs[0]["id"].lower())["count"]
            == _busca(client, h, uf=ufs[0]["id"])["count"]
        )


def test_cidades_trazem_o_estado(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    j = client.get(
        f"{settings.API_V1_STR}/leads/opcoes", headers=superuser_token_headers
    ).json()
    ids = {u["id"] for u in j["ufs"]}
    assert all(c["uf"] in ids for c in j["cidades"])


def test_busca_por_cnpj(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    h = superuser_token_headers
    um = _busca(client, h)["data"][0]["cnpj"]
    # com pontuação e mesmo com outro filtro marcado, acha aquela empresa
    fmt = f"{um[:2]}.{um[2:5]}.{um[5:8]}/{um[8:12]}-{um[12:]}"
    j = _busca(client, h, cnpj=fmt, celular=True, uf="XX")
    assert [x["cnpj"] for x in j["data"]] == [um]
    # 8 dígitos = matriz e filiais
    basico = _busca(client, h, cnpj=um[:8])["data"]
    assert basico and all(x["cnpj"].startswith(um[:8]) for x in basico)
    assert _busca(client, h, cnpj="99999999999999")["count"] == 0


def test_busca_por_cnae(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    h = superuser_token_headers
    cnaes = client.get(f"{settings.API_V1_STR}/leads/opcoes", headers=h).json()["cnaes"]
    if not cnaes:
        pytest.skip("receita.cnaes vazia")
    c = cnaes[0]["id"]
    assert cnaes[0]["nome"].startswith(f"{c[:4]}-{c[4]}/{c[5:]}")
    princ = _busca(client, h, cnae=f"{c[:4]}-{c[4]}/{c[5:]}")
    assert all(x["cnae"] == c for x in princ["data"])
    sec = _busca(client, h, cnae=c, cnae_em="secundario")["count"]
    ambos = _busca(client, h, cnae=c, cnae_em="ambos")["count"]
    assert ambos >= max(princ["count"], sec)
    # dois códigos somam
    outro = cnaes[1]["id"] if len(cnaes) > 1 else c
    dois = _busca(client, h, cnae=[c, outro])["count"]
    assert dois == princ["count"] + (
        _busca(client, h, cnae=outro)["count"] if outro != c else 0
    )
    assert _busca(client, h, cnae="123")["count"] == 0
