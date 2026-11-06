"""Onda 1, Etapa 2 (T2.2): estágio oficial do COP (RF-01), malha dos bairros e prioridade por vulnerabilidade
(RF-06, RF-22)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from climasense.territorio import carga
from tests.conftest import precisa_postgres
from tests.integration.apoio import Relogio, cliente, criar_conta, entrar

pytestmark = [precisa_postgres, pytest.mark.integracao]
API = "/api/v1"


@pytest.fixture
def equipe(sessao):
    carga.sincronizar_territorios(sessao, carga.geo_local())
    relogio = Relogio()
    contas = {"relogio": relogio}
    for nome, papeis in (("analista", ["analista"]), ("leitor", ["revisor"])):
        criar_conta(sessao, f"{nome}@recife.pe.gov.br", papeis, nome=nome.capitalize())
        c = cliente(sessao, relogio)
        assert entrar(c, f"{nome}@recife.pe.gov.br").status_code == 200
        contas[nome] = c
    return contas


# ------------------------------------------------------------------ 1. estágio oficial
def test_sem_registro_estagio_oficial_e_nulo_e_nunca_observacao(equipe):
    r = equipe["leitor"].get(f"{API}/estagios/oficial")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["dados"] is None
    assert corpo["meta"]["dados_insuficientes"] is True
    assert corpo["meta"]["fontes"][0]["atualizado_em"] is None
    lista = equipe["leitor"].get(f"{API}/estagios").json()
    assert lista["meta"]["estagio_oficial"] is None
    assert equipe["leitor"].get(f"{API}/estagios/oficial/historico").json()["dados"] == []


def test_analista_registra_estagio_oficial_e_ele_aparece_na_lista(equipe, sessao):
    relogio = equipe["relogio"]
    informado = relogio.agora - timedelta(hours=1)
    r = equipe["analista"].post(
        f"{API}/estagios/oficial",
        json={
            "estagio": "alerta",
            "informado_em": informado.isoformat(),
            "observacao": "  Comunicado   do COP ",
        },
    )
    assert r.status_code == 201, r.text
    d = r.json()["dados"]
    assert d["estagio"] == "alerta" and d["autor_nome"] == "Analista"
    assert d["observacao"] == "Comunicado do COP"
    assert d["fonte"] == "COP (informado pela equipe)"
    assert d["informado_em"].startswith(informado.strftime("%Y-%m-%dT%H:%M"))
    vigente = equipe["leitor"].get(f"{API}/estagios/oficial").json()["dados"]
    assert vigente["estagio"] == "alerta"
    assert equipe["leitor"].get(f"{API}/estagios").json()["meta"]["estagio_oficial"]["estagio"] == "alerta"
    auditoria = sessao.execute(
        text("select count(*) from app.auditoria where acao = 'estagio_oficial_registrado'")
    ).scalar()
    assert auditoria == 1


def test_estagio_oficial_nao_altera_o_declarado_nem_o_sugerido(equipe):
    antes = equipe["leitor"].get(f"{API}/estagios").json()["dados"]["itens"]
    equipe["analista"].post(f"{API}/estagios/oficial", json={"estagio": "critico"})
    depois = equipe["leitor"].get(f"{API}/estagios").json()["dados"]["itens"]
    assert [(i["sugerido"]["estagio"], i["declarado"]) for i in antes] == [
        (i["sugerido"]["estagio"], i["declarado"]) for i in depois
    ]


def test_vigente_e_o_informado_mais_recente_e_o_historico_guarda_tudo(equipe):
    relogio = equipe["relogio"]
    a = equipe["analista"]

    def h(n: int) -> str:
        return (relogio.agora - timedelta(hours=n)).isoformat()

    a.post(f"{API}/estagios/oficial", json={"estagio": "atencao", "informado_em": h(5)})
    a.post(f"{API}/estagios/oficial", json={"estagio": "critico", "informado_em": h(2)})
    a.post(f"{API}/estagios/oficial", json={"estagio": "observacao", "informado_em": h(9)})
    assert a.get(f"{API}/estagios/oficial").json()["dados"]["estagio"] == "critico"
    hist = [i["estagio"] for i in a.get(f"{API}/estagios/oficial/historico").json()["dados"]]
    assert hist == ["critico", "atencao", "observacao"]


def test_registro_oficial_exige_login_e_valida_o_corpo(equipe, sessao):
    relogio = equipe["relogio"]
    anonimo = cliente(sessao, relogio)
    assert anonimo.post(f"{API}/estagios/oficial", json={"estagio": "alerta"}).status_code == 401
    assert anonimo.get(f"{API}/estagios/oficial").status_code == 401
    assert anonimo.get(f"{API}/territorios/prioridade").status_code == 401
    a = equipe["analista"]
    assert a.post(f"{API}/estagios/oficial", json={"estagio": "sem_dados"}).status_code == 422
    assert a.post(f"{API}/estagios/oficial", json={"estagio": "encerrado"}).status_code == 422
    futuro = (relogio.agora + timedelta(hours=2)).isoformat()
    r = a.post(f"{API}/estagios/oficial", json={"estagio": "alerta", "informado_em": futuro})
    assert r.status_code == 422 and "futuro" in r.json()["detail"]
    sem_fuso = {"estagio": "alerta", "informado_em": "2026-10-15T10:00:00"}
    assert a.post(f"{API}/estagios/oficial", json=sem_fuso).status_code == 422
    assert (
        a.post(f"{API}/estagios/oficial", json={"estagio": "alerta", "observacao": "x" * 501}).status_code
        == 422
    )


def test_historico_oficial_e_somente_inclusao(equipe, sessao):
    equipe["analista"].post(f"{API}/estagios/oficial", json={"estagio": "alerta"})
    for sql in ("update app.estagio_oficial set estagio = 'critico'", "delete from app.estagio_oficial"):
        with pytest.raises(DBAPIError), sessao.begin_nested():
            sessao.execute(text(sql))


# ------------------------------------------------------------------ 2. malha de bairros
def test_malha_de_bairros_tem_94_bairros_com_os_mesmos_ids_de_estagios(equipe):
    c = equipe["leitor"]
    r = c.get(f"{API}/territorios/bairros.geojson")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/geo+json")
    assert "max-age" in r.headers["cache-control"]
    geo = r.json()
    assert geo["type"] == "FeatureCollection" and len(geo["features"]) == 94
    assert len(r.content) < 300_000  # simplificada
    for f in geo["features"]:
        assert set(f["properties"]) == {"id", "nome", "distrito_id"}
        assert f["properties"]["id"].startswith("bairro-") and f["properties"]["distrito_id"].startswith(
            "ds-"
        )
    ids_malha = {f["properties"]["id"] for f in geo["features"]}
    ids_estagios = {
        i["territorio_id"]
        for i in c.get(f"{API}/estagios", params={"nivel": "bairro"}).json()["dados"]["itens"]
    }
    assert ids_malha == ids_estagios
    condicional = c.get(f"{API}/territorios/bairros.geojson", headers={"If-None-Match": r.headers["etag"]})
    assert condicional.status_code == 304


# ------------------------------------------------------------------ 3. prioridade por vulnerabilidade
def _carga_ocorrencias(sessao, linhas: list[tuple[str, str, str]]) -> None:
    ex = sessao.execute(
        text(
            "insert into app.etl_execucoes (fonte_id, status, fim) "
            "values ('recife-alagamento', 'sucesso', now()) returning id"
        )
    ).scalar_one()
    for territorio, tipo, dia in linhas:
        sessao.execute(
            text(
                "insert into silver.ocorrencias (fonte_id, territorio_id, registrado_em, tipo, execucao_id) "
                "values ('recife-alagamento', :t, :d, :tipo, :e)"
            ),
            {"t": territorio, "d": dia, "tipo": tipo, "e": ex},
        )


def test_prioridade_sem_carga_nao_ordena_nada(equipe):
    r = equipe["leitor"].get(f"{API}/territorios/prioridade")
    assert r.status_code == 200
    assert r.json()["dados"]["itens"] == []
    assert r.json()["meta"]["dados_insuficientes"] is True


def test_prioridade_ordena_pelo_historico_real_e_explica_o_criterio(equipe, sessao):
    pai = dict(sessao.execute(text("select id, pai_id from app.territorios where tipo = 'bairro'")).all())
    a, b, c = "bairro-boa-viagem", "bairro-ibura", "bairro-casa-amarela"
    assert all(i in pai for i in (a, b, c))
    _carga_ocorrencias(
        sessao,
        [(a, "alagamento", "2014-03-01")] * 2
        + [(a, "deslizamento", "2016-05-01")]
        + [(b, "alagamento", "2015-01-01")] * 5
        + [(c, "deslizamento", "2020-01-01")] * 5,
    )
    r = equipe["leitor"].get(f"{API}/territorios/prioridade", params={"nivel": "bairro"})
    assert r.status_code == 200, r.text
    corpo = r.json()
    itens = corpo["dados"]["itens"]
    assert len(itens) == 94 and {i["nivel"] for i in itens} == {"bairro"}
    # b (5 alagamentos) e c (5 deslizamentos) empatam em 5 atendimentos; b sai antes por ter mais alagamento
    assert [(i["territorio_id"], i["posicao"]) for i in itens[:3]] == [(b, 1), (c, 2), (a, 3)]
    assert itens[0]["ocorrencias_alagamento"] == 5 and itens[0]["ocorrencias_deslizamento"] == 0
    assert itens[2]["ocorrencias_alagamento"] == 2 and itens[2]["ocorrencias_deslizamento"] == 1
    assert itens[-1]["ocorrencias_alagamento"] == 0  # zero medido, não ausente (RN-02)
    assert corpo["dados"]["desde"] == 2014
    assert itens[0]["criterio"] == "mais atendimentos de alagamento e deslizamento desde 2014"
    assert corpo["meta"]["dados_insuficientes"] is False
    assert corpo["meta"]["fontes"][0]["id"] == "recife-alagamento"
    assert "%" not in r.text


def test_prioridade_sem_nivel_traz_distritos_e_bairros_somando_os_bairros(equipe, sessao):
    pai = dict(sessao.execute(text("select id, pai_id from app.territorios where tipo = 'bairro'")).all())
    a, b = "bairro-boa-viagem", "bairro-pina"
    ds = pai[a]
    _carga_ocorrencias(sessao, [(a, "alagamento", "2018-01-01")] * 3 + [(b, "deslizamento", "2018-01-01")])
    itens = equipe["leitor"].get(f"{API}/territorios/prioridade").json()["dados"]["itens"]
    distritos = [i for i in itens if i["nivel"] == "distrito"]
    assert len(distritos) == 8 and len(itens) == 102
    esperado = 3 + (1 if pai[b] == ds else 0)
    d = next(i for i in distritos if i["territorio_id"] == ds)
    assert d["ocorrencias_alagamento"] + d["ocorrencias_deslizamento"] == esperado
    assert d["posicao"] == 1
    assert equipe["leitor"].get(f"{API}/territorios/prioridade", params={"nivel": "x"}).status_code == 422
