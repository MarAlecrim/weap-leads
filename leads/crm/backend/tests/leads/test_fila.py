"""Fila do disparo (sdr_fila no banco do agente). Precisa de um banco weap_sdr local com a tabela;
sem ele, os testes são pulados. URL em AGENTE_DB_URL_TESTE."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import settings
from app.leads import repo

URL = os.environ.get("AGENTE_DB_URL_TESTE", "")


@pytest.fixture()
def agente(monkeypatch: pytest.MonkeyPatch):
    if not URL:
        pytest.skip("sem banco do agente de teste (AGENTE_DB_URL_TESTE)")
    eng = create_engine(URL)
    with eng.connect() as c:
        if not c.execute(text("SELECT to_regclass('sdr_fila') IS NOT NULL")).scalar():
            pytest.skip("banco do agente sem sdr_fila")
    monkeypatch.setattr(settings, "AGENTE_DB_URL", URL)
    repo._engine_agente.cache_clear()
    yield eng
    repo._engine_agente.cache_clear()


def _linha(zap: str, no_disparo: bool = False) -> dict:
    return {
        "whatsapp": zap,
        "no_disparo": no_disparo,
        "nome": "Empresa Teste",
        "endereco": "Rua A, 1",
        "cidade": "Londrina",
        "atividade": "Construção de edifícios",
        "decisor": "Fulano",
        "email": "",
        "cnpj": "00000000000191",
        "nota": 80,
    }


def test_sem_banco_do_agente(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AGENTE_DB_URL", None)
    repo._engine_agente.cache_clear()
    with pytest.raises(repo.SemBancoDoAgente):
        repo.mandar_para_fila([_linha("43999990001")], "teste")
    assert repo.resumo_fila() is None


def test_mandar_para_fila_sem_repetir(agente) -> None:
    zaps = ["43999990001", "43999990002"]
    try:
        r = repo.mandar_para_fila(
            [
                _linha(zaps[0]),
                _linha(zaps[1]),
                _linha("", False),
                _linha("43999990003", True),
            ],
            "teste",
        )
        assert r == {"adicionados": 2, "ja_no_disparo": 1, "sem_whatsapp": 1}
        # de novo: os dois já estão na fila e passam a contar como "no disparo"
        assert repo.chaves_no_disparo({"554399990001", "554399990002"}) == {
            "554399990001",
            "554399990002",
        }
        r = repo.mandar_para_fila([_linha(zaps[0])], "teste")
        assert r["adicionados"] == 0 and r["ja_no_disparo"] == 1
        resumo = repo.resumo_fila()
        assert resumo is not None and resumo["aguardando"] >= 2
        with agente.connect() as c:
            t = c.execute(
                text("SELECT telefone FROM sdr_fila WHERE chave = '554399990001'")
            ).scalar()
        assert t == "5543999990001@s.whatsapp.net"
    finally:
        with agente.begin() as c:
            c.execute(text("DELETE FROM sdr_fila WHERE criado_por = 'teste'"))


def test_rota_fila_sem_banco(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "AGENTE_DB_URL", None)
    repo._engine_agente.cache_clear()
    r = client.get(f"{settings.API_V1_STR}/leads/fila", headers=superuser_token_headers)
    assert r.status_code == 200 and r.json() is None
    r = client.post(
        f"{settings.API_V1_STR}/leads/disparo",
        headers=superuser_token_headers,
        json={"filtros": {"celular": False}, "cnpjs": ["00000000000000"]},
    )
    assert r.status_code == 503
