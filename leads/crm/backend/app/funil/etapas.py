"""Etapas do funil, serviços com valor sugerido e motivos de perda (docs: especificação da fase 2)."""

ETAPAS: list[tuple[str, str]] = [
    ("fila", "Na fila"),
    ("contatado", "Contatado"),
    ("respondeu", "Respondeu"),
    ("interessado", "Interessado"),
    ("reuniao", "Reunião marcada"),
    ("proposta", "Proposta enviada"),
    ("negociacao", "Negociação"),
    ("ganho", "Ganho"),
    ("perdido", "Perdido"),
]
NOMES = dict(ETAPAS)
ORDEM = {e: i for i, (e, _) in enumerate(ETAPAS)}
FECHADAS = {"ganho", "perdido"}

# Status que o agente grava em sdr_leads -> etapa do funil (e motivo, quando perde).
DO_AGENTE: dict[str, tuple[str, str | None]] = {
    "contatado": ("contatado", None),
    "respondeu": ("respondeu", None),
    "interessado": ("interessado", None),
    "humano": ("interessado", None),
    "agendamento_pendente": ("reuniao", None),
    "agendado": ("reuniao", None),
    "sem_interesse": ("perdido", "Sem interesse"),
    "bot": ("perdido", "Robô ou atendimento automático"),
}

# Valor sugerido (tabela Weap). A pessoa ajusta no card.
SERVICOS: list[tuple[str, str, int]] = [
    ("landing", "Landing page", 35_000),
    ("site", "Site", 75_000),
    ("site_pro", "Site Profissional", 170_000),
    ("site_completo", "Site completo", 250_000),
    ("gmn", "Google Meu Negócio", 35_000),
    ("redes_4", "Instagram, 4 artes/mês", 27_000),
    ("redes_6", "Instagram, 6 artes/mês", 37_000),
    ("redes_12", "Instagram, 12 artes/mês", 57_000),
    ("marca", "Marca com manual", 95_000),
    ("outro", "Outro", 0),
]
VALOR_SERVICO = {s: v for s, _, v in SERVICOS}

MOTIVOS_PERDA = [
    "Sem interesse",
    "Preço",
    "Já tem fornecedor",
    "Sem resposta",
    "Robô ou atendimento automático",
    "Pediu para não receber",
    "Outro",
]

DIAS_ALERTA = 3  # "sem resposta" e "parado" a partir de 3 dias


def etapa_do_agente(
    status: str | None, opt_out: bool, fila_status: str | None
) -> tuple[str, str | None] | None:
    """Etapa que o agente indica para o lead, ou None se ele não deve estar no funil."""
    if opt_out:
        return ("perdido", "Pediu para não receber")
    if status:
        return DO_AGENTE.get(status, ("contatado", None))
    if fila_status in ("novo", "pegando"):
        return ("fila", None)
    if fila_status == "enviado":
        return ("contatado", None)
    return None


def pode_avancar(atual: str, nova: str) -> bool:
    """O automático só empurra para a frente e não mexe em ganho/perdido.
    "Perdido" vindo do agente só vale até "Reunião marcada": depois disso quem decide é a pessoa."""
    if atual in FECHADAS or nova == atual:
        return False
    if nova == "perdido":
        return ORDEM[atual] <= ORDEM["reuniao"]
    return ORDEM[nova] > ORDEM[atual]
