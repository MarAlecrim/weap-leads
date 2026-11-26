"""Conexão dos números na Evolution (sem rede: httpx.get é trocado nos testes)."""

from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.leads import evolution

API = f"{settings.API_V1_STR}/leads/numeros/conexao"


class _Resp:
    def __init__(self, dados: Any, status: int = 200) -> None:
        self._dados, self.status_code = dados, status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("erro", request=None, response=None)  # type: ignore[arg-type]

    def json(self) -> Any:
        return self._dados


@pytest.fixture(autouse=True)
def limpa_cache() -> None:
    evolution._cache.update(em=0.0, estados=None)


def _servidores(monkeypatch: pytest.MonkeyPatch, valor: str) -> None:
    monkeypatch.setattr(settings, "EVOLUTION_APIS", valor)


def test_sem_configuracao(monkeypatch: pytest.MonkeyPatch) -> None:
    _servidores(monkeypatch, "")
    assert evolution.conexoes() == {"configurado": False, "estados": {}, "falhas": []}


def test_junta_v1_e_v2_e_falhas(monkeypatch: pytest.MonkeyPatch) -> None:
    _servidores(
        monkeypatch,
        "https://zap7.x/|k1; https://outra.x|k2 ;https://caiu.x|k3;semchave",
    )
    chamadas: list[tuple[str, str]] = []

    def get(url: str, headers: dict[str, str], **_kw: Any) -> _Resp:
        chamadas.append((url, headers["apikey"]))
        if "zap7" in url:
            return _Resp(
                [
                    {"name": "Weap-7533", "connectionStatus": "open"},
                    {"name": "Weap-Agente-Novo-4815", "connectionStatus": "close"},
                ]
            )
        if "outra" in url:
            return _Resp(
                [
                    {
                        "instance": {
                            "instanceName": "Weap-8526-1094",
                            "status": "connecting",
                        }
                    }
                ]
            )
        return _Resp({}, 500)

    monkeypatch.setattr(httpx, "get", get)
    r = evolution.conexoes()
    assert r["estados"] == {
        "Weap-7533": "conectado",
        "Weap-Agente-Novo-4815": "desconectado",
        "Weap-8526-1094": "conectando",
    }
    assert r["falhas"] == ["caiu.x"]
    assert chamadas[0] == ("https://zap7.x/instance/fetchInstances", "k1")
    assert len(chamadas) == 3
    # guarda por 30 s: não pergunta de novo
    evolution.conexoes()
    assert len(chamadas) == 3


def test_rota_so_administrador(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _servidores(monkeypatch, "")
    assert client.get(API, headers=normal_user_token_headers).status_code == 403
    r = client.get(API, headers=superuser_token_headers)
    assert r.status_code == 200 and r.json()["configurado"] is False
