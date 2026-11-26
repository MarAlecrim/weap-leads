"""Situação da conexão de cada número na Evolution API (zap7 e as outras).

Os servidores e as chaves ficam só no .env do servidor, em EVOLUTION_APIS:
    EVOLUTION_APIS=https://zap7.exemplo.com.br|CHAVE;https://outra.exemplo.com.br|CHAVE2
Para cada servidor o CRM chama /instance/fetchInstances uma vez e junta pelo nome da instância.
"""

import logging
import time
from typing import Any

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)

GUARDA_SEGUNDOS = 30  # não pergunta à Evolution mais de uma vez a cada 30 s
_cache: dict[str, Any] = {
    "em": 0.0,
    "estados": None,
}  # estados: resultado de conexoes()

# estado da Evolution -> estado mostrado na tela
ESTADOS = {"open": "conectado", "connecting": "conectando", "close": "desconectado"}


def servidores() -> list[tuple[str, str]]:
    out = []
    for parte in settings.EVOLUTION_APIS.split(";"):
        url, _, chave = parte.strip().partition("|")
        if url.strip() and chave.strip():
            out.append((url.strip().rstrip("/"), chave.strip()))
    return out


def _le(item: dict[str, Any]) -> tuple[str | None, str | None]:
    """Aceita o formato da Evolution v2 ({name, connectionStatus}) e da v1 ({instance: {instanceName, status}})."""
    if "name" in item:
        return item.get("name"), item.get("connectionStatus")
    inst = item.get("instance") or {}
    return inst.get("instanceName"), inst.get("status") or inst.get("state")


def _busca(url: str, chave: str) -> dict[str, str]:
    r = httpx.get(
        f"{url}/instance/fetchInstances", headers={"apikey": chave}, timeout=8
    )
    r.raise_for_status()
    estados: dict[str, str] = {}
    for item in r.json() or []:
        nome, st = _le(item if isinstance(item, dict) else {})
        if nome:
            estados[nome] = ESTADOS.get(
                str(st or "").lower(), str(st or "desconhecido")
            )
    return estados


def conexoes() -> dict[str, Any]:
    """{"configurado": bool, "estados": {instancia: estado}, "falhas": [servidor]}.
    Instância que não aparece em nenhum servidor fica de fora (a tela mostra "não achado")."""
    srv = servidores()
    if not srv:
        return {"configurado": False, "estados": {}, "falhas": []}
    agora = time.monotonic()
    guardado: dict[str, Any] | None = _cache["estados"]
    if guardado is not None and agora - _cache["em"] < GUARDA_SEGUNDOS:
        return guardado
    estados: dict[str, str] = {}
    falhas: list[str] = []
    for url, chave in srv:
        try:
            estados |= _busca(url, chave)
        except Exception:
            log.exception("Falha ao consultar a Evolution em %s", url)
            falhas.append(httpx.URL(url).host)
    res: dict[str, Any] = {"configurado": True, "estados": estados, "falhas": falhas}
    _cache.update(em=agora, estados=res)
    return res
