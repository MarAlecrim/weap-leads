"""Caixa de conversas. Precisa do banco do agente de teste (AGENTE_DB_URL_TESTE); sem ele, pula."""

import os
from collections.abc import Generator
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlmodel import Session, col, delete, select

from app import crud
from app.core.config import settings
from app.funil import sincronia
from app.leads import repo
from app.models import ConversaLida, Negocio, UserCreate
from tests.utils.user import user_authentication_headers
from tests.utils.utils import random_email, random_lower_string

API = f"{settings.API_V1_STR}/conversas"
URL = os.environ.get("AGENTE_DB_URL_TESTE", "")


def _apagar(eng: Engine, db: Session) -> None:
    with eng.begin() as c:
        c.execute(text("DELETE FROM sdr_leads WHERE chave LIKE '5599%'"))
    db.execute(delete(Negocio).where(col(Negocio.chave).like("5599%")))
    db.execute(delete(ConversaLida).where(col(ConversaLida.chave).like("5599%")))
    db.commit()


@pytest.fixture()
def agente(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> Generator[Engine, None, None]:
    if not URL:
        pytest.skip("sem banco do agente de teste (AGENTE_DB_URL_TESTE)")
    eng = create_engine(URL)
    _apagar(eng, db)
    with eng.begin() as c:
        a = c.execute(
            text(
                "INSERT INTO sdr_leads (chave, whatsapp, instancia, nome_empresa, status) VALUES "
                "('5599000000021', '559900000021', 'Conv-1111', 'Padaria A', 'respondeu') RETURNING id"
            )
        ).scalar()
        b = c.execute(
            text(
                "INSERT INTO sdr_leads (chave, whatsapp, instancia, nome_empresa, status, opt_out) VALUES "
                "('5599000000022', '559900000022', 'Conv-2222', 'Oficina B', 'sem_interesse', true) RETURNING id"
            )
        ).scalar()
        s = c.execute(
            text(
                "INSERT INTO sdr_leads (chave, whatsapp, instancia, nome_empresa, status) VALUES "
                "('5599000000023', '559900000023', 'Conv-1111', 'Só disparo', 'contatado') RETURNING id"
            )
        ).scalar()
        c.execute(
            text(
                "INSERT INTO sdr_mensagens (lead_id, instancia, direcao, autor, texto) VALUES "
                "(:a, 'Conv-1111', 'out', 'disparo', 'Oi, tudo bem?'),"
                "(:b, 'Conv-2222', 'out', 'disparo', 'Oi!'),"
                "(:b, 'Conv-2222', 'in', 'lead', 'Não tenho interesse'),"
                "(:a, 'Conv-1111', 'in', 'lead', 'Quanto custa um site?'),"
                "(:s, 'Conv-1111', 'out', 'disparo', 'Oi?')"
            ),
            {"a": a, "b": b, "s": s},
        )
    monkeypatch.setattr(settings, "AGENTE_DB_URL", URL)
    repo._engine_agente.cache_clear()
    yield eng
    repo._engine_agente.cache_clear()
    _apagar(eng, db)


def _vendedor(client: TestClient, db: Session, numeros: list[str]) -> dict[str, str]:
    email, senha = random_email(), random_lower_string()
    crud.create_user(
        session=db,
        user_create=UserCreate(
            email=email, password=senha, perfil="vendedor", numeros=numeros
        ),
    )
    return user_authentication_headers(client=client, email=email, password=senha)


@pytest.mark.usefixtures("agente")
def test_lista_e_lidas(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.get(f"{API}/", headers=superuser_token_headers)
    assert r.status_code == 200
    d = r.json()
    nomes = [c["nome"] for c in d["conversas"] if c["chave"].startswith("5599")]
    # a mais recente primeiro; quem só recebeu o disparo não aparece
    assert nomes == ["Padaria A", "Oficina B"]
    assert d["conversas"][0]["ultima_texto"] == "Quanto custa um site?"
    assert d["conversas"][0]["numero"] == "1111"
    nao_lidas_antes = d["nao_lidas"]
    assert nao_lidas_antes >= 2

    r = client.get(f"{API}/5599000000021", headers=superuser_token_headers)
    assert r.status_code == 200
    assert [m["autor"] for m in r.json()["mensagens"]] == ["disparo", "lead"]

    d = client.get(
        f"{API}/", headers=superuser_token_headers, params={"nao_lidas": True}
    ).json()
    chaves = [c["chave"] for c in d["conversas"]]
    assert "5599000000021" not in chaves and "5599000000022" in chaves
    assert d["nao_lidas"] == nao_lidas_antes - 1

    so_1111 = client.get(
        f"{API}/", headers=superuser_token_headers, params={"instancia": "Conv-2222"}
    ).json()
    assert {c["chave"] for c in so_1111["conversas"]} == {"5599000000022"}
    busca = client.get(
        f"{API}/", headers=superuser_token_headers, params={"busca": "padaria"}
    ).json()
    assert [c["chave"] for c in busca["conversas"]] == ["5599000000021"]


@pytest.mark.usefixtures("agente")
def test_vendedor_ve_so_o_dele(client: TestClient, db: Session) -> None:
    h = _vendedor(client, db, ["Conv-1111"])
    d = client.get(f"{API}/", headers=h).json()
    assert [c["chave"] for c in d["conversas"]] == ["5599000000021"]
    assert client.get(f"{API}/5599000000022", headers=h).status_code == 404
    assert client.get(f"{API}/5599000000021", headers=h).status_code == 200


def test_responder_pausa_e_retomar(
    agente: Engine,
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sincronia.aplicar(
        db,
        [
            {
                "chave": "5599000000021",
                "telefone": "559900000021",
                "instancia": "Conv-1111",
                "nome_empresa": "Padaria A",
                "status": "respondeu",
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
        ],
    )
    # sem a chave da Evolution, responder fica desligado
    monkeypatch.setattr(settings, "EVOLUTION_API_KEY", None)
    r = client.post(
        f"{API}/5599000000021/responder",
        headers=superuser_token_headers,
        json={"texto": "Oi"},
    )
    assert r.status_code == 503

    enviados: list[dict[str, Any]] = []

    def falso_post(url: str, **kw: Any) -> httpx.Response:
        enviados.append({"url": url, **kw})
        return httpx.Response(201, json={"key": {"id": "MSG-TESTE-1", "fromMe": True}})

    monkeypatch.setattr(settings, "EVOLUTION_API_KEY", "chave-de-teste")
    monkeypatch.setattr(settings, "EVOLUTION_URL", "https://evo.exemplo/")
    monkeypatch.setattr(httpx, "post", falso_post)
    r = client.post(
        f"{API}/5599000000021/responder",
        headers=superuser_token_headers,
        json={"texto": "Olá! Te ligo em 5 min."},
    )
    assert r.status_code == 200, r.text
    c = r.json()
    assert c["ia_pausada"] is True and c["status"] == "humano"
    assert c["mensagens"][-1]["autor"] == "humano"
    assert enviados[0]["url"] == "https://evo.exemplo/message/sendText/Conv-1111"
    assert enviados[0]["json"] == {
        "number": "559900000021",
        "text": "Olá! Te ligo em 5 min.",
    }
    with agente.connect() as cx:
        assert (
            cx.execute(
                text("SELECT count(*) FROM sdr_mensagens WHERE msg_id = 'MSG-TESTE-1'")
            ).scalar()
            == 1
        )
    db.expire_all()
    n = db.exec(select(Negocio).where(Negocio.chave == "5599000000021")).one()
    assert n.ia_pausada is True

    # quem pediu para sair não recebe
    r = client.post(
        f"{API}/5599000000022/responder",
        headers=superuser_token_headers,
        json={"texto": "Oi"},
    )
    assert r.status_code == 409

    # WhatsApp recusou
    monkeypatch.setattr(
        httpx, "post", lambda url, **kw: httpx.Response(400, json={"erro": "x"})
    )
    r = client.post(
        f"{API}/5599000000021/responder",
        headers=superuser_token_headers,
        json={"texto": "Oi de novo"},
    )
    assert r.status_code == 502

    r = client.post(f"{API}/5599000000021/retomar", headers=superuser_token_headers)
    assert r.status_code == 200
    assert r.json()["ia_pausada"] is False and r.json()["status"] == "respondeu"
    db.expire_all()
    n = db.exec(select(Negocio).where(Negocio.chave == "5599000000021")).one()
    assert n.ia_pausada is False


def test_sem_banco_do_agente(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "AGENTE_DB_URL", None)
    repo._engine_agente.cache_clear()
    d = client.get(f"{API}/", headers=superuser_token_headers).json()
    assert d["ligado_ao_agente"] is False and d["conversas"] == []
    assert (
        client.get(f"{API}/5599000000021", headers=superuser_token_headers).status_code
        == 404
    )
    repo._engine_agente.cache_clear()
