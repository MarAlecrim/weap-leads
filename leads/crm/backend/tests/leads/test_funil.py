"""Funil (kanban): etapas automáticas a partir do agente, permissões por perfil e mudança à mão."""

from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, delete, select

from app import crud
from app.core.config import settings
from app.funil import etapas, sincronia
from app.models import Negocio, NegocioHistorico, NegocioNota, UserCreate, UserUpdate
from tests.utils.user import user_authentication_headers
from tests.utils.utils import random_email, random_lower_string

API = f"{settings.API_V1_STR}/funil"


@pytest.fixture()
def limpo(db: Session) -> Generator[None, None, None]:
    def apagar() -> None:
        db.execute(delete(Negocio).where(col(Negocio.chave).like("5599%")))
        db.commit()

    apagar()
    yield
    apagar()


def _linha(chave: str, **kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "chave": chave,
        "telefone": chave,
        "instancia": "Teste-1111",
        "nome_empresa": "Empresa " + chave[-2:],
        "status": None,
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
    base.update(kw)
    return base


def _negocio(db: Session, chave: str) -> Negocio:
    db.expire_all()
    n = db.exec(select(Negocio).where(Negocio.chave == chave)).one()
    return n


def test_etapa_do_agente() -> None:
    assert etapas.etapa_do_agente(None, False, "novo") == ("fila", None)
    assert etapas.etapa_do_agente(None, False, "pulado") is None
    assert etapas.etapa_do_agente("agendado", False, None) == ("reuniao", None)
    assert etapas.etapa_do_agente("respondeu", True, None) == (
        "perdido",
        "Pediu para não receber",
    )
    assert etapas.etapa_do_agente("bot", False, None)[0] == "perdido"  # type: ignore[index]


def test_pode_avancar() -> None:
    assert etapas.pode_avancar("contatado", "respondeu")
    assert not etapas.pode_avancar("interessado", "respondeu")
    assert not etapas.pode_avancar("ganho", "perdido")
    assert etapas.pode_avancar("reuniao", "perdido")
    assert not etapas.pode_avancar("proposta", "perdido")


@pytest.mark.usefixtures("limpo")
def test_sincronia_cria_e_so_avanca(db: Session) -> None:
    sincronia.aplicar(
        db,
        [
            _linha(
                "5599000000001",
                fila_status="novo",
                origem="receita",
                nota=88,
                cidade="Londrina",
            ),
            _linha("5599000000002", status="respondeu"),
            _linha("5599000000003", fila_status="pulado"),
        ],
    )
    a = _negocio(db, "5599000000001")
    assert (a.etapa, a.origem, a.nota, a.cidade) == ("fila", "receita", 88, "Londrina")
    assert _negocio(db, "5599000000002").etapa == "respondeu"
    assert (
        db.exec(select(Negocio).where(Negocio.chave == "5599000000003")).first() is None
    )

    # o disparo mandou e o lead respondeu
    sincronia.aplicar(
        db,
        [
            _linha(
                "5599000000001",
                status="respondeu",
                fila_status="enviado",
                origem="receita",
            )
        ],
    )
    a = _negocio(db, "5599000000001")
    assert a.etapa == "respondeu"
    hist = db.exec(
        select(NegocioHistorico).where(NegocioHistorico.negocio_id == a.id)
    ).all()
    assert [(h.de, h.para, h.autor) for h in hist] == [
        (None, "fila", "agente"),
        ("fila", "respondeu", "agente"),
    ]

    # alguém levou à mão para "proposta": o agente não volta nem perde o card
    a.etapa = "proposta"
    db.add(a)
    db.commit()
    sincronia.aplicar(db, [_linha("5599000000001", status="sem_interesse")])
    assert _negocio(db, "5599000000001").etapa == "proposta"

    # antes da proposta, "sem interesse" leva para perdido com o motivo
    sincronia.aplicar(db, [_linha("5599000000002", status="sem_interesse")])
    b = _negocio(db, "5599000000002")
    assert (b.etapa, b.perdido_motivo) == ("perdido", "Sem interesse")


@pytest.mark.usefixtures("limpo")
def test_sincronia_tira_da_fila_quem_saiu(db: Session) -> None:
    sincronia.aplicar(
        db,
        [
            _linha("5599000000031", fila_status="novo"),
            _linha("5599000000032", fila_status="novo"),
            _linha("5599000000033", fila_status="novo"),
            _linha("5599000000034", fila_status="pegando"),
        ],
    )
    com_nota = _negocio(db, "5599000000033")
    db.add(NegocioNota(negocio_id=com_nota.id, texto="ligar depois", autor="Teste"))
    db.commit()
    # 31 e 33 foram retirados da fila (não aparecem mais), 32 recebeu o disparo, 34 segue enviando.
    sincronia.aplicar(
        db,
        [
            _linha("5599000000032", status="contatado", fila_status="enviado"),
            _linha("5599000000034", fila_status="pegando"),
        ],
        limpar_fila=True,
    )
    db.expire_all()
    assert (
        db.exec(select(Negocio).where(Negocio.chave == "5599000000031")).first() is None
    )
    assert _negocio(db, "5599000000032").etapa == "contatado"
    assert _negocio(db, "5599000000033").etapa == "fila"
    assert _negocio(db, "5599000000034").etapa == "fila"


@pytest.mark.usefixtures("limpo")
def test_responsavel_pelo_numero(db: Session) -> None:
    vend = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=random_email(),
            password=random_lower_string(),
            perfil="vendedor",
            numeros=["Teste-1111"],
        ),
    )
    sincronia.aplicar(db, [_linha("5599000000004", status="contatado")])
    assert _negocio(db, "5599000000004").responsavel_id == vend.id
    crud.update_user(session=db, db_user=vend, user_in=UserUpdate(numeros=[]))


def test_perfil_admin_e_superuser(db: Session) -> None:
    u = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=random_email(), password=random_lower_string(), perfil="admin"
        ),
    )
    assert u.is_superuser
    u = crud.update_user(session=db, db_user=u, user_in=UserUpdate(perfil="gestor"))
    assert not u.is_superuser and u.perfil == "gestor"


@pytest.mark.usefixtures("limpo")
def test_rotas_do_funil(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
) -> None:
    agora = datetime.now(timezone.utc)
    sincronia.aplicar(
        db,
        [
            _linha(
                "5599000000005",
                status="contatado",
                ultimo_contato_em=agora - timedelta(days=5),
            ),
            _linha("5599000000006", status="respondeu", instancia="Outro-2222"),
        ],
    )
    r = client.get(f"{API}/", headers=superuser_token_headers)
    assert r.status_code == 200
    colunas = {c["etapa"]: c for c in r.json()["colunas"]}
    assert list(colunas) == [e for e, _ in etapas.ETAPAS]
    card = next(c for c in colunas["contatado"]["cards"] if c["nome"] == "Empresa 05")
    assert card["dias_sem_resposta"] == 5 and card["numero"] == "1111"

    nid = card["id"]
    r = client.patch(
        f"{API}/{nid}", headers=superuser_token_headers, json={"etapa": "perdido"}
    )
    assert r.status_code == 422
    r = client.patch(
        f"{API}/{nid}",
        headers=superuser_token_headers,
        json={"etapa": "proposta", "servico": "site_pro"},
    )
    assert r.status_code == 200
    assert (r.json()["etapa"], r.json()["valor_cents"]) == ("proposta", 170_000)

    # vendedor só vê os leads dos seus números
    senha = random_lower_string()
    email = random_email()
    vend = crud.create_user(
        session=db,
        user_create=UserCreate(email=email, password=senha, numeros=["Teste-1111"]),
    )
    h = user_authentication_headers(client=client, email=email, password=senha)
    r = client.get(f"{API}/", headers=h)
    nomes = {c["nome"] for col_ in r.json()["colunas"] for c in col_["cards"]}
    assert "Empresa 05" in nomes and "Empresa 06" not in nomes
    outro = _negocio(db, "5599000000006")
    assert (
        client.patch(
            f"{API}/{outro.id}", headers=h, json={"valor_cents": 100}
        ).status_code
        == 404
    )
    crud.update_user(session=db, db_user=vend, user_in=UserUpdate(numeros=[]))

    r = client.get(f"{API}/opcoes", headers=superuser_token_headers)
    assert r.status_code == 200 and r.json()["motivos"]


@pytest.mark.usefixtures("limpo")
def test_ler_agente_de_verdade(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """Roda a consulta no banco do agente de teste (AGENTE_DB_URL_TESTE), se houver."""
    import os

    from sqlalchemy import create_engine, text

    from app.leads import repo

    url = os.environ.get("AGENTE_DB_URL_TESTE", "")
    if not url:
        pytest.skip("sem banco do agente de teste")
    eng = create_engine(url)
    with eng.begin() as c:
        c.execute(text("DELETE FROM sdr_leads WHERE chave LIKE '5599%'"))
        c.execute(text("DELETE FROM sdr_fila WHERE chave LIKE '5599%'"))
        c.execute(
            text(
                "INSERT INTO sdr_leads (chave, telefone, instancia, nome_empresa, status) "
                "VALUES ('5599000000007', '5599000000007', 'Teste-1111', 'Lead do agente', 'interessado')"
            )
        )
        c.execute(
            text(
                "INSERT INTO sdr_fila (chave, telefone, nome_empresa, nota, origem) "
                "VALUES ('5599000000008', '5599000000008', 'Lead da fila', 77, 'receita')"
            )
        )
    monkeypatch.setattr(settings, "AGENTE_DB_URL", url)
    repo._engine_agente.cache_clear()
    try:
        assert sincronia.sincronizar(db, forcar=True)
        assert _negocio(db, "5599000000007").etapa == "interessado"
        f = _negocio(db, "5599000000008")
        assert (f.etapa, f.nota, f.origem) == ("fila", 77, "receita")
    finally:
        repo._engine_agente.cache_clear()
        with eng.begin() as c:
            c.execute(text("DELETE FROM sdr_leads WHERE chave LIKE '5599%'"))
            c.execute(text("DELETE FROM sdr_fila WHERE chave LIKE '5599%'"))


@pytest.mark.usefixtures("limpo")
def test_ficha_com_notas(
    client: TestClient, db: Session, superuser_token_headers: dict[str, str]
) -> None:
    sincronia.aplicar(db, [_linha("5599000000009", status="respondeu")])
    n = _negocio(db, "5599000000009")
    r = client.get(f"{API}/{n.id}", headers=superuser_token_headers)
    assert r.status_code == 200
    f = r.json()
    assert f["conversa_disponivel"] is False and f["mensagens"] == []
    assert [h["para"] for h in f["historico"]] == ["respondeu"]
    r = client.post(
        f"{API}/{n.id}/notas",
        headers=superuser_token_headers,
        json={"texto": "Tem 2 unidades"},
    )
    assert r.status_code == 200
    assert r.json()["notas"][0]["texto"] == "Tem 2 unidades"
    assert (
        client.post(
            f"{API}/{n.id}/notas", headers=superuser_token_headers, json={"texto": ""}
        ).status_code
        == 422
    )


@pytest.mark.usefixtures("limpo")
def test_conversa_do_agente(monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    from sqlalchemy import create_engine, text

    from app.leads import repo

    url = os.environ.get("AGENTE_DB_URL_TESTE", "")
    if not url:
        pytest.skip("sem banco do agente de teste")
    eng = create_engine(url)
    with eng.begin() as c:
        c.execute(text("DELETE FROM sdr_leads WHERE chave LIKE '5599%'"))
        lid = c.execute(
            text(
                "INSERT INTO sdr_leads (chave, resumo) VALUES ('5599000000010', 'Quer site') RETURNING id"
            )
        ).scalar()
        c.execute(
            text(
                "INSERT INTO sdr_mensagens (lead_id, direcao, autor, texto) VALUES "
                "(:l, 'out', 'disparo', 'Oi!'), (:l, 'in', 'lead', 'Quanto custa?')"
            ),
            {"l": lid},
        )
    monkeypatch.setattr(settings, "AGENTE_DB_URL", url)
    repo._engine_agente.cache_clear()
    try:
        conv = sincronia.conversa("5599000000010")
        assert conv is not None and conv["resumo"] == "Quer site"
        assert [m["autor"] for m in conv["mensagens"]] == ["disparo", "lead"]
        assert sincronia.conversa("5599000000099") == {"resumo": None, "mensagens": []}
    finally:
        repo._engine_agente.cache_clear()
        with eng.begin() as c:
            c.execute(text("DELETE FROM sdr_leads WHERE chave LIKE '5599%'"))


@pytest.mark.usefixtures("limpo")
def test_painel(
    client: TestClient, db: Session, superuser_token_headers: dict[str, str]
) -> None:
    agora = datetime.now(timezone.utc)
    sincronia.aplicar(
        db,
        [
            _linha("5599000000011", status="contatado"),
            _linha("5599000000012", status="respondeu", ultima_resposta_em=agora),
            _linha("5599000000013", status="sem_interesse", ultima_resposta_em=agora),
            _linha("5599000000014", fila_status="novo"),
        ],
    )
    r = client.get(f"{settings.API_V1_STR}/painel/", headers=superuser_token_headers)
    assert r.status_code == 200
    p = r.json()
    assert p["contatados"] >= 3 and p["responderam"] >= 2
    assert [e["etapa"] for e in p["etapas"]] == [e for e, _ in etapas.ETAPAS]
    num = next(x for x in p["por_numero"] if x["instancia"] == "Teste-1111")
    assert (num["contatados"], num["responderam"]) == (3, 2)


def test_ordenar_cards() -> None:
    from app.api.routes.funil import ordenar

    agora = datetime.now(timezone.utc)
    a = _card_teste(1, "Beta", contato=agora - timedelta(days=2), nota=90)
    b = _card_teste(2, "alfa", contato=agora, resposta=agora - timedelta(days=5))
    c = _card_teste(3, "Gama", nota=50, dias=7)  # na fila, sem contato
    d = _card_teste(4, "Delta", contato=agora - timedelta(days=1), resposta=agora)

    def ids(ordem: str) -> list[int]:
        return [x.id for x in ordenar([a, b, c, d], ordem)]

    assert ids("recente") == [2, 4, 1, 3]
    assert ids("qualquer") == [2, 4, 1, 3]  # desconhecida cai no padrão
    assert ids("antigo") == [1, 4, 2, 3]
    assert ids("resposta") == [4, 2, 1, 3]
    assert ids("nota") == [1, 3, 2, 4]  # empate: ordem de chegada
    assert ids("parado") == [3, 1, 2, 4]
    assert ids("nome") == [2, 1, 4, 3]


def _card_teste(
    id: int,
    nome: str,
    contato: datetime | None = None,
    resposta: datetime | None = None,
    nota: int | None = None,
    dias: int = 0,
) -> Any:
    from app.api.routes.funil import Card

    return Card(
        id=id,
        nome=nome,
        cnpj=None,
        cidade=None,
        origem="receita",
        nota=nota,
        instancia=None,
        numero=None,
        responsavel_id=None,
        responsavel=None,
        etapa="contatado",
        valor_cents=None,
        servico=None,
        dias_na_etapa=dias,
        dias_sem_resposta=None,
        ia_pausada=False,
        proxima_acao=None,
        proxima_acao_em=None,
        perdido_motivo=None,
        ultimo_contato_em=contato,
        ultima_resposta_em=resposta,
    )


@pytest.mark.usefixtures("limpo")
def test_funil_ordem_padrao_mais_recente(
    client: TestClient, db: Session, superuser_token_headers: dict[str, str]
) -> None:
    agora = datetime.now(timezone.utc)
    sincronia.aplicar(
        db,
        [
            _linha(
                "5599000000021",
                status="contatado",
                ultimo_contato_em=agora - timedelta(days=3),
                nota=99,
            ),
            _linha("5599000000022", status="contatado", ultimo_contato_em=agora),
        ],
    )
    r = client.get(
        f"{API}/", headers=superuser_token_headers, params={"busca": "Empresa 2"}
    )
    col_ = next(c for c in r.json()["colunas"] if c["etapa"] == "contatado")
    nomes = [c["nome"] for c in col_["cards"]]
    assert nomes.index("Empresa 22") < nomes.index("Empresa 21")
    r = client.get(
        f"{API}/",
        headers=superuser_token_headers,
        params={"busca": "Empresa 2", "ordem": "antigo"},
    )
    col_ = next(c for c in r.json()["colunas"] if c["etapa"] == "contatado")
    nomes = [c["nome"] for c in col_["cards"]]
    assert nomes.index("Empresa 21") < nomes.index("Empresa 22")
    assert col_["cards"][0]["ultimo_contato_em"]


def test_montar_desempenho() -> None:
    from datetime import date

    from app.api.routes.funil import montar_desempenho

    hoje = date(2026, 11, 27)
    ontem = date(2026, 11, 26)

    def lin(
        inst: str | None, dia: date | None, emp: int, abord: int, resp: int
    ) -> dict[str, Any]:
        return {
            "instancia": inst,
            "dia": dia,
            "sem_inst": int(inst is None),
            "sem_dia": int(dia is None),
            "empresas": emp,
            "abordagens": abord,
            "respostas": resp,
            "ultimo_envio": None,
        }

    linhas = [
        lin("Weap-Fabiano-7187", hoje, 10, 10, 2),
        lin("Weap-Fabiano-7187", ontem, 5, 5, 1),
        lin("Weap-Fabiano-7187", None, 14, 15, 3),  # 1 lead abordado nos dois dias
        lin("Weap-7407", ontem, 4, 4, 0),
        lin("Weap-7407", None, 4, 4, 0),
        lin(None, hoje, 10, 10, 2),
        lin(None, ontem, 9, 9, 1),
        lin(None, None, 18, 19, 3),
    ]
    d = montar_desempenho(linhas, {"Weap-Fabiano-7187": "7187 · Fabiano"}, 3, hoje)
    assert d.disponivel and d.dias == 3
    assert (d.total.empresas, d.total.mensagens, d.total.respostas) == (18, 38, 3)
    assert d.hoje.empresas == 10
    assert [n.nome for n in d.numeros] == ["7187 · Fabiano", "7407"]
    f = d.numeros[0]
    assert (f.empresas, f.mensagens, f.hoje.empresas, f.hoje.mensagens) == (
        14,
        30,
        10,
        20,
    )
    assert d.numeros[1].hoje.empresas == 0
    assert [x.dia for x in d.por_dia] == [hoje, ontem, date(2026, 11, 25)]
    assert [x.empresas for x in d.por_dia] == [10, 9, 0]


def test_desempenho_sem_agente(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.get(
        f"{API}/desempenho", headers=superuser_token_headers, params={"dias": 7}
    )
    assert r.status_code == 200
    d = r.json()
    if not settings.AGENTE_DB_URL:
        assert d["disponivel"] is False and len(d["por_dia"]) == 7
    assert (
        client.get(
            f"{API}/desempenho", headers=superuser_token_headers, params={"dias": 0}
        ).status_code
        == 422
    )


def test_desempenho_do_agente_de_verdade(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Roda a consulta de desempenho no banco do agente de teste (AGENTE_DB_URL_TESTE), se houver."""
    import os

    from sqlalchemy import create_engine, text

    from app.leads import repo

    url = os.environ.get("AGENTE_DB_URL_TESTE", "")
    if not url:
        pytest.skip("sem banco do agente de teste")
    eng = create_engine(url)
    inst = "Teste-Desemp-9911"
    with eng.begin() as c:
        c.execute(text("DELETE FROM sdr_leads WHERE chave LIKE '559911%'"))
        ids = [
            c.execute(
                text(
                    "INSERT INTO sdr_leads (chave, instancia) VALUES (:c, :i) RETURNING id"
                ),
                {"c": f"559911000000{k}", "i": inst},
            ).scalar()
            for k in range(3)
        ]
        for lid in ids:
            c.execute(
                text(
                    "INSERT INTO sdr_mensagens (lead_id, instancia, direcao, autor, texto) "
                    "VALUES (:l, :i, 'out', 'disparo', 'Oi')"
                ),
                {"l": lid, "i": inst},
            )
        # resposta sem instância na mensagem: vale a do lead; e a IA não conta
        c.execute(
            text(
                "INSERT INTO sdr_mensagens (lead_id, instancia, direcao, autor, texto) VALUES "
                "(:l, NULL, 'in', 'lead', 'Quanto?'), (:l, :i, 'out', 'ia', 'R$ 350'),"
                "(:l, :i, 'in', 'lead', 'Ok')"
            ),
            {"l": ids[0], "i": inst},
        )
        # disparo de 2 dias atrás
        c.execute(
            text(
                "INSERT INTO sdr_mensagens (lead_id, instancia, direcao, autor, texto, criado_em) "
                "VALUES (:l, :i, 'out', 'disparo', 'Oi', now() - interval '2 days')"
            ),
            {"l": ids[1], "i": inst},
        )
    monkeypatch.setattr(settings, "AGENTE_DB_URL", url)
    repo._engine_agente.cache_clear()
    try:
        r = client.get(
            f"{API}/desempenho",
            headers=superuser_token_headers,
            params={"instancia": inst, "dias": 7},
        )
        assert r.status_code == 200
        d = r.json()
        assert d["disponivel"]
        assert [n["instancia"] for n in d["numeros"]] == [inst]
        n = d["numeros"][0]
        assert (n["empresas"], n["mensagens"], n["respostas"]) == (3, 8, 1)
        assert (n["hoje"]["empresas"], n["hoje"]["respostas"]) == (3, 1)
        assert d["por_dia"][0]["empresas"] == 3 and d["por_dia"][2]["empresas"] == 1
        assert d["total"]["empresas"] == 3
        todos = client.get(f"{API}/desempenho", headers=superuser_token_headers).json()
        assert inst in [x["instancia"] for x in todos["numeros"]]
    finally:
        repo._engine_agente.cache_clear()
        with eng.begin() as c:
            c.execute(text("DELETE FROM sdr_leads WHERE chave LIKE '559911%'"))
