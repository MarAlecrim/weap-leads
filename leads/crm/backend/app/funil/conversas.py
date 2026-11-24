"""Caixa de conversas: as conversas do WhatsApp de todos os números, guardadas pelo agente
no banco dele (weap_sdr: sdr_leads + sdr_mensagens).

- A lista mostra só quem já falou (o lead respondeu ou alguém da Weap escreveu), da mais
  recente para a mais antiga.
- "Lida" fica no banco do CRM (crm_conversa_lida), por usuário: até qual mensagem ele já viu.
- Responder manda pela Evolution, pelo mesmo número que conversa com o lead, grava a
  mensagem como "humano" e pausa a IA desse lead (como quando alguém escreve pelo celular).
  "Retomar" devolve a conversa para a IA.
- O que chega do lead continua entrando pelo n8n; aqui só se lê.
"""

import logging
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy import text

from app.core.config import settings
from app.leads import repo

log = logging.getLogger(__name__)

POR_PAGINA = 40


class SemEvolution(Exception):
    """O CRM não tem a URL ou a chave da Evolution no .env."""


class NaoPodeEnviar(Exception):
    """O lead não pode receber mensagem (pediu para sair ou não tem número)."""


class EvolutionFalhou(Exception):
    pass


# Conversas: um lead aparece se já tem mensagem do lead ou de alguém da Weap.
_SQL_LISTA = """
WITH lidas AS (
  SELECT * FROM unnest(CAST(:lidas_chave AS text[]), CAST(:lidas_ate AS bigint[])) AS t(chave, ate)
)
SELECT l.id AS lead_id, l.chave, coalesce(nullif(l.nome_empresa, ''), nullif(l.nome_contato, ''), l.chave) AS nome,
       l.instancia, l.status, l.ia_pausada, l.opt_out,
       u.id AS ultima_id, u.texto AS ultima_texto, u.autor AS ultima_autor, u.criado_em AS ultima_em,
       coalesce(nl.qtd, 0) AS nao_lidas
  FROM sdr_leads l
  CROSS JOIN LATERAL (
    SELECT m.id, m.texto, m.autor, m.criado_em FROM sdr_mensagens m
     WHERE m.lead_id = l.id ORDER BY m.id DESC LIMIT 1
  ) u
  LEFT JOIN lidas ON lidas.chave = l.chave
  CROSS JOIN LATERAL (
    SELECT count(*) AS qtd FROM sdr_mensagens m
     WHERE m.lead_id = l.id AND m.direcao = 'in' AND m.id > coalesce(lidas.ate, 0)
  ) nl
 WHERE EXISTS (SELECT 1 FROM sdr_mensagens m WHERE m.lead_id = l.id AND m.autor IN ('lead', 'humano'))
   AND (:todas OR l.instancia = ANY(CAST(:numeros AS text[])) OR l.chave = ANY(CAST(:extra AS text[])))
   AND (CAST(:instancia AS text) IS NULL OR l.instancia = :instancia)
   AND (CAST(:busca AS text) IS NULL OR l.nome_empresa ILIKE :busca OR l.nome_contato ILIKE :busca
        OR l.chave LIKE :busca_dig)
   {filtro}
"""


def _params(
    todas: bool,
    numeros: list[str],
    extra: list[str],
    lidas: dict[str, int],
    instancia: str | None,
    busca: str | None,
) -> dict[str, Any]:
    b = (busca or "").strip()
    dig = "".join(ch for ch in b if ch.isdigit())
    return {
        "todas": todas,
        "numeros": numeros or [""],
        "extra": extra or [""],
        "lidas_chave": list(lidas.keys()),
        "lidas_ate": list(lidas.values()),
        "instancia": instancia or None,
        "busca": f"%{b}%" if b else None,
        "busca_dig": f"%{dig}%" if len(dig) >= 4 else "-",
    }


def listar(
    *,
    todas: bool,
    numeros: list[str],
    extra: list[str],
    lidas: dict[str, int],
    instancia: str | None = None,
    so_nao_lidas: bool = False,
    busca: str | None = None,
    antes: int | None = None,
    limite: int = POR_PAGINA,
) -> dict[str, Any] | None:
    """Conversas visíveis para quem pediu, da mais recente para a mais antiga.
    `todas` = vê todos os números; senão só `numeros` (instâncias) e os leads `extra` (chaves).
    `antes` = id da última mensagem da página anterior (para "Carregar mais").
    None se o CRM não está ligado ao agente."""
    eng = repo._engine_agente()
    if not eng:
        return None
    p = _params(todas, numeros, extra, lidas, instancia, busca)
    filtro = ""
    if so_nao_lidas:
        filtro += " AND nl.qtd > 0"
    pagina = filtro
    if antes:
        pagina += " AND u.id < :antes"
        p["antes"] = antes
    with eng.connect() as c:
        linhas = c.execute(
            text(
                _SQL_LISTA.format(filtro=pagina) + " ORDER BY u.id DESC LIMIT :limite"
            ),
            p | {"limite": limite + 1},
        ).mappings()
        conversas = [dict(r) for r in linhas]
        nao_lidas = c.execute(
            text(
                "SELECT count(*) FROM ("
                + _SQL_LISTA.format(filtro=" AND nl.qtd > 0")
                + ") x"
            ),
            p,
        ).scalar_one()
    return {
        "conversas": conversas[:limite],
        "tem_mais": len(conversas) > limite,
        "nao_lidas": nao_lidas,
    }


def lead(chave: str) -> dict[str, Any] | None:
    """O lead no banco do agente (None se não existe ou se o CRM não está ligado)."""
    eng = repo._engine_agente()
    if not eng:
        return None
    with eng.connect() as c:
        r = (
            c.execute(
                text(
                    """SELECT id, chave, coalesce(nullif(nome_empresa, ''), nullif(nome_contato, ''), chave) AS nome,
                              coalesce(whatsapp, telefone) AS numero, instancia, status, ia_pausada,
                              opt_out, resumo
                         FROM sdr_leads WHERE chave = :c"""
                ),
                {"c": chave},
            )
            .mappings()
            .first()
        )
        return dict(r) if r else None


def mensagens(lead_id: int, limite: int = 300) -> list[dict[str, Any]]:
    eng = repo._engine_agente()
    if not eng:
        return []
    with eng.connect() as c:
        return [
            dict(m)
            for m in c.execute(
                text(
                    """SELECT * FROM (
                         SELECT id, direcao, autor, texto, instancia, criado_em
                           FROM sdr_mensagens WHERE lead_id = :id ORDER BY id DESC LIMIT :lim
                       ) m ORDER BY id"""
                ),
                {"id": lead_id, "lim": limite},
            ).mappings()
        ]


def _evolution_url() -> str:
    if settings.EVOLUTION_URL:
        return settings.EVOLUTION_URL.rstrip("/")
    eng = repo._engine_agente()
    if eng:
        with eng.connect() as c:
            url = c.execute(
                text("SELECT valor FROM sdr_config WHERE chave = 'evolution_url'")
            ).scalar()
        if url and url.startswith("http") and "SUA-EVOLUTION" not in url:
            return str(url).rstrip("/")
    raise SemEvolution()


def _enviar_evolution(instancia: str, numero: str, texto: str) -> str | None:
    """Manda o texto pela Evolution. Devolve o id da mensagem no WhatsApp."""
    if not settings.EVOLUTION_API_KEY:
        raise SemEvolution()
    url = f"{_evolution_url()}/message/sendText/{instancia}"
    try:
        r = httpx.post(
            url,
            json={"number": numero, "text": texto},
            headers={"apikey": settings.EVOLUTION_API_KEY},
            timeout=30,
        )
    except httpx.HTTPError as e:
        log.warning("Evolution não respondeu: %s", type(e).__name__)
        raise EvolutionFalhou("A Evolution não respondeu. Tente de novo.") from e
    if r.status_code >= 400:
        log.warning("Evolution recusou o envio: %s %s", r.status_code, r.text[:300])
        raise EvolutionFalhou(
            "O WhatsApp recusou o envio. Confira se o número está conectado."
        )
    try:
        corpo = r.json()
    except ValueError:
        return None
    chave = corpo.get("key") if isinstance(corpo, dict) else None
    return str(chave.get("id")) if isinstance(chave, dict) and chave.get("id") else None


def responder(chave: str, texto: str) -> dict[str, Any]:
    """Manda a resposta pelo número do lead, grava como "humano" e pausa a IA.
    Devolve a mensagem gravada."""
    eng = repo._engine_agente()
    if not eng:
        raise SemEvolution()
    ld = lead(chave)
    if not ld:
        raise NaoPodeEnviar("Esse lead não está no banco do agente.")
    if ld["opt_out"]:
        raise NaoPodeEnviar("Esse lead pediu para não receber mensagens.")
    if not ld["numero"] or not ld["instancia"]:
        raise NaoPodeEnviar("Esse lead não tem número ou número da Weap definido.")
    msg_id = _enviar_evolution(ld["instancia"], ld["numero"], texto)
    with eng.begin() as c:
        # o n8n também recebe essa mensagem (fromMe) e grava como "humano": o msg_id evita duplicar
        gravada = (
            c.execute(
                text(
                    """INSERT INTO sdr_mensagens (lead_id, instancia, direcao, autor, texto, msg_id)
                       SELECT :lead, :inst, 'out', 'humano', :texto, :msg
                        WHERE CAST(:msg AS text) IS NULL
                           OR NOT EXISTS (SELECT 1 FROM sdr_mensagens WHERE msg_id = :msg)
                       RETURNING id, direcao, autor, texto, instancia, criado_em"""
                ),
                {
                    "lead": ld["id"],
                    "inst": ld["instancia"],
                    "texto": texto,
                    "msg": msg_id,
                },
            )
            .mappings()
            .first()
        )
        c.execute(
            text(
                """UPDATE sdr_leads
                      SET ia_pausada = true,
                          status = CASE WHEN status IN ('agendado', 'sem_interesse', 'bot') THEN status
                                        ELSE 'humano' END,
                          ultimo_contato_em = now(),
                          atualizado_em = now()
                    WHERE id = :id"""
            ),
            {"id": ld["id"]},
        )
    if gravada:
        return dict(gravada)
    return {
        "id": 0,
        "direcao": "out",
        "autor": "humano",
        "texto": texto,
        "instancia": ld["instancia"],
        "criado_em": datetime.now().astimezone(),
    }


def retomar(chave: str) -> bool:
    """A IA volta a responder esse lead. False se o lead não existe."""
    eng = repo._engine_agente()
    if not eng:
        return False
    with eng.begin() as c:
        r = c.execute(
            text(
                """UPDATE sdr_leads
                      SET ia_pausada = false,
                          status = CASE WHEN status = 'humano' THEN 'respondeu' ELSE status END,
                          atualizado_em = now()
                    WHERE chave = :c RETURNING id"""
            ),
            {"c": chave},
        ).first()
    return r is not None
