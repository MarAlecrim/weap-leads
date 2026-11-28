"""Formatação de nomes, telefones e endereços vindos da Receita (tudo em maiúsculas)."""

import re
from datetime import date

PORTES = {
    "01": "Microempresa",
    "03": "Pequeno porte",
    "05": "Demais",
    "00": "Não informado",
}

# A Receita só informa micro (01), pequeno porte (03) e "demais" (05). O MEI vem do arquivo do
# Simples, e média x grande é separada pelo capital social (a Receita não distingue).
CAPITAL_GRANDE = 10_000_000
FAIXAS = {
    "mei": "MEI",
    "me": "Microempresa",
    "epp": "Pequeno porte",
    "media": "Média",
    "grande": "Grande",
}


def faixa(porte: str | None, mei: bool | None, capital: float | None) -> str:
    """Código da faixa de porte usada na tela."""
    if mei:
        return "mei"
    if porte == "01":
        return "me"
    if porte == "03":
        return "epp"
    if porte == "05":
        return "grande" if (capital or 0) > CAPITAL_GRANDE else "media"
    return ""


# Nome de cada estado, para o filtro da busca
UFS = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AM": "Amazonas",
    "AP": "Amapá",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MG": "Minas Gerais",
    "MS": "Mato Grosso do Sul",
    "MT": "Mato Grosso",
    "PA": "Pará",
    "PB": "Paraíba",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "PR": "Paraná",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RO": "Rondônia",
    "RR": "Roraima",
    "RS": "Rio Grande do Sul",
    "SC": "Santa Catarina",
    "SE": "Sergipe",
    "SP": "São Paulo",
    "TO": "Tocantins",
}


NICHOS_NOME = {
    "saude": "Saúde",
    "construcao": "Construção",
    "estetica": "Estética",
    "imobiliaria": "Imobiliária",
    "veterinaria": "Veterinária",
    "nutricao": "Nutrição",
    "farmacia": "Farmácia",
    "otica": "Ótica",
    "salao de beleza": "Salão de beleza",
    "materiais de construcao": "Materiais de construção",
    "moveis planejados": "Móveis planejados",
}

_MINUSCULAS = {"Da", "De", "Do", "Das", "Dos", "E"}
_MAIUSCULAS = {"Ltda", "Me", "Epp", "S/A", "Sa"}


def nome_nicho(n: str) -> str:
    return NICHOS_NOME.get(n, n[:1].upper() + n[1:])


def nome_bonito(s: str | None) -> str:
    if not s:
        return ""
    t = s.lower().title()

    def troca(m: re.Match[str]) -> str:
        w = m.group(1)
        if w in _MAIUSCULAS:
            return w.upper()
        return w.lower()

    return re.sub(r"\b(Da|De|Do|Das|Dos|E|Ltda|Me|Epp|S/A|Sa)\b", troca, t)


def e_celular(t: str | None) -> bool:
    return bool(t) and re.fullmatch(r"[1-9][0-9]9[0-9]{8}", t or "") is not None


def whatsapp(t1: str | None, t2: str | None) -> str:
    for t in (t1, t2):
        if e_celular(t):
            return t or ""
    return ""


def chave(t: str | None) -> str | None:
    """Mesma chave do banco do agente: 55 + DDD + 8 últimos dígitos."""
    x = re.sub(r"\D", "", t or "")
    d = x[2:] if len(x) >= 12 and x.startswith("55") else x.lstrip("0")
    if len(d) < 10:
        return None
    return "55" + d[:2] + d[-8:]


def fone_bonito(t: str | None) -> str:
    t = t or ""
    if len(t) == 11:
        return f"({t[:2]}) {t[2:7]}-{t[7:]}"
    if len(t) == 10:
        return f"({t[:2]}) {t[2:6]}-{t[6:]}"
    return t


def endereco(r: dict) -> str:  # type: ignore[type-arg]
    rua = nome_bonito(r.get("logradouro"))
    if r.get("numero"):
        rua = f"{rua}, {r['numero']}"
    partes = [p for p in [rua.strip(), nome_bonito(r.get("bairro"))] if p]
    cidade = nome_bonito(r.get("cidade"))
    if cidade:
        partes.append(f"{cidade} - {r.get('uf') or ''}".strip(" -"))
    s = " - ".join(partes)
    cep = r.get("cep") or ""
    if len(cep) == 8:
        s += f", {cep[:5]}-{cep[5:]}"
    return s


def anos(d: date | None) -> int | None:
    if not d:
        return None
    hoje = date.today()
    return hoje.year - d.year - ((hoje.month, hoje.day) < (d.month, d.day))


def cnae(c: str | None) -> str:
    """4781400 vira 4781-4/00 (como aparece no cartão CNPJ)."""
    c = c or ""
    return f"{c[:4]}-{c[4]}/{c[5:]}" if len(c) == 7 and c.isdigit() else c
