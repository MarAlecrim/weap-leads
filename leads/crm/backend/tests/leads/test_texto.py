from datetime import date

from app.leads import texto


def test_nome_bonito() -> None:
    assert (
        texto.nome_bonito("OFICINA DO JOAO E FILHOS LTDA")
        == "Oficina do Joao e Filhos LTDA"
    )
    assert texto.nome_bonito(None) == ""


def test_celular_e_whatsapp() -> None:
    assert texto.e_celular("41991348881")
    assert not texto.e_celular("4133334444")
    assert texto.whatsapp("4133334444", "41991348881") == "41991348881"
    assert texto.whatsapp("4133334444", None) == ""


def test_chave_igual_ao_banco_do_agente() -> None:
    assert texto.chave("5541991348881@s.whatsapp.net") == "554191348881"
    assert texto.chave("41991348881") == "554191348881"
    assert texto.chave("123") is None


def test_endereco_e_fone() -> None:
    r = {
        "logradouro": "RUA XV DE NOVEMBRO",
        "numero": "10",
        "bairro": "CENTRO",
        "cidade": "CURITIBA",
        "uf": "PR",
        "cep": "80020310",
    }
    assert (
        texto.endereco(r)
        == "Rua Xv de Novembro, 10 - Centro - Curitiba - PR, 80020-310"
    )
    assert texto.fone_bonito("41991348881") == "(41) 99134-8881"


def test_anos() -> None:
    assert texto.anos(None) is None
    assert texto.anos(date(date.today().year - 3, 1, 1)) == 3
