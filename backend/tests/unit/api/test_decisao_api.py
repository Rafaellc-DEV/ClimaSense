"""Rotas de apoio à decisão (/territorios/prioridades), sem banco: o serviço
é substituído por dados controlados e conferimos envelope, degradação e papéis."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from climasense.api import autorizacao
from climasense.api.envelope import FonteMeta
from climasense.api.main import criar_app
from climasense.api.routers import painel, territorios
from climasense.dominio import cenario
from climasense.infra.postgres import obter_sessao
from climasense.servicos import decisao
from tests.conftest import configuracao_teste

AGORA = datetime(2026, 10, 15, 20, 30, tzinfo=UTC)


class Resultado:
    def __init__(self, linhas):
        self.linhas = linhas

    def all(self):
        return self.linhas

    def __iter__(self):
        return iter(self.linhas)


class BancoFalso:
    def __init__(self, distritos=(), bairros=(), ocorrencias=()):
        self.distritos, self.bairros, self.ocorr = list(distritos), list(bairros), list(ocorrencias)

    def execute(self, stmt, params=None):
        sql = str(stmt)
        if "tipo = 'distrito'" in sql:
            return Resultado(self.distritos)
        if "tipo = 'bairro'" in sql:
            return Resultado(self.bairros)
        if "silver.ocorrencias" in sql:
            return Resultado(self.ocorr)
        return Resultado([])


def _est(prioridade, acumulado=60.0, p95=50.0, qualidade="completa"):
    return cenario.Estimativa(
        prioridade=prioridade,
        qualidade="insuficiente" if prioridade == "dados_insuficientes" else qualidade,
        janela_atencao=None,
        fatores=[("Chuva prevista acima do comum", "60,0 mm em 24 h")],
        limitacoes=["Falta a previsão de maré."]
        if prioridade == "dados_insuficientes"
        else ["Regra de referência."],
        acumulado_previsto_mm=None if prioridade == "dados_insuficientes" else acumulado,
        p95_mm=p95,
        p99_mm=80.0,
    )


@pytest.fixture
def servico(monkeypatch):
    estimativas = {"ds-1": _est("atencao"), "ds-2": _est("alerta", 90.0), "ds-3": _est("dados_insuficientes")}
    monkeypatch.setattr(
        decisao.cenarios,
        "emitir",
        lambda db, ds, h, agora, registrar=True: {"estimativa": estimativas[ds], "emissoes_na_faixa": 4},
    )
    monkeypatch.setattr(decisao, "frescor", lambda db, agora, ids=decisao.FONTES_CHAVE: [])
    monkeypatch.setattr(decisao.cenarios, "ocorrencias", lambda db, t: None)
    return estimativas


def test_prioridades_ordenam_e_nao_tratam_insuficiente_como_seguro(servico):
    db = BancoFalso([("ds-1", "DS I"), ("ds-2", "DS II"), ("ds-3", "DS III")])
    itens = decisao.prioridades(db, "distrito", 72, AGORA, [])
    assert [i["territorio_id"] for i in itens] == ["ds-2", "ds-1", "ds-3"]
    assert [i["posicao"] for i in itens] == [1, 2, 3]
    ds3 = itens[2]
    assert ds3["nivel"] == "dados_insuficientes" and ds3["confianca"] == "insuficiente"
    assert ds3["acumulado_previsto_mm"] is None  # nunca um zero inventado
    assert ds3["motivos"][0]["origem"] == "qualidade" and "maré" in ds3["motivos"][0]["descricao"]
    assert all(i["experimental"] for i in itens)
    assert {e["tipo"] for e in itens[0]["evidencias"]} == {"cenario", "serie", "mapa"}
    assert itens[0]["evidencias"][0]["parametros"] == {"territorio_id": "ds-2", "horizonte_h": "72"}


def test_aviso_vigente_sobe_o_nivel_e_aparece_nos_motivos(servico):
    aviso = SimpleNamespace(nivel="critico", titulo="Chuva forte", territorios=[SimpleNamespace(id="ds-1")])
    db = BancoFalso([("ds-1", "DS I"), ("ds-2", "DS II"), ("ds-3", "DS III")])
    itens = decisao.prioridades(db, "distrito", 72, AGORA, [aviso])
    assert itens[0]["territorio_id"] == "ds-1"
    assert itens[0]["nivel"] == "critico" and itens[0]["nivel_estimador"] == "atencao"
    assert any(m["origem"] == "aviso" for m in itens[0]["motivos"])


def test_bairro_herda_o_distrito_e_avisa(servico, monkeypatch):
    monkeypatch.setattr(decisao.cenarios, "ocorrencias", lambda db, t: 5)
    db = BancoFalso(
        [("ds-1", "DS I"), ("ds-2", "DS II"), ("ds-3", "DS III")],
        bairros=[("bairro-a", "A", "ds-2"), ("bairro-b", "B", "ds-2"), ("bairro-c", "C", "ds-1")],
        ocorrencias=[("bairro-b", 9)],
    )
    itens = decisao.prioridades(db, "bairro", 72, AGORA, [])
    assert [i["territorio_id"] for i in itens] == ["bairro-b", "bairro-a", "bairro-c"]
    assert itens[0]["ocorrencias_historicas"] == 9 and itens[1]["ocorrencias_historicas"] == 0
    assert any("só por distrito" in m["descricao"] for m in itens[0]["motivos"])
    assert (
        decisao.prioridades(db, "bairro", 72, AGORA, [], distrito_id="ds-1")[0]["territorio_id"] == "bairro-c"
    )


def test_fonte_com_falha_vira_nota_e_rebaixa_confianca(servico, monkeypatch):
    fr = [{"fonte_id": "open-meteo-previsao", "nome": "Previsão", "status": "com_falha"}]
    monkeypatch.setattr(decisao, "frescor", lambda db, agora, ids=decisao.FONTES_CHAVE: fr)
    item = decisao.prioridades(BancoFalso([("ds-1", "DS I")]), "distrito", 72, AGORA, [])[0]
    assert item["confianca"] == "baixa"
    assert any("com falha" in n for n in item["notas_qualidade"])


# ---------------------------------------------------------------- HTTP
def _cliente(monkeypatch, papeis=("analista",)):
    app = criar_app(configuracao_teste())
    ctx = autorizacao.Contexto(
        usuario=SimpleNamespace(id=uuid.uuid4(), papeis=list(papeis)), sessao=None, ip=None
    )
    for rota in (painel.consultar, territorios.consultar):
        app.dependency_overrides[rota] = lambda: ctx
    app.dependency_overrides[obter_sessao] = lambda: object()
    app.dependency_overrides[autorizacao.relogio] = lambda: AGORA

    def meta(db, f, agora):
        return FonteMeta(id=f, nome=f, tipo="prevista", status="planejada")

    monkeypatch.setattr(painel.servico_fontes, "meta", meta)
    return TestClient(app, raise_server_exceptions=True)


def test_prioridades_http(monkeypatch, servico):
    c = _cliente(monkeypatch)
    db = BancoFalso([("ds-1", "DS I"), ("ds-2", "DS II"), ("ds-3", "DS III")])
    c.app.dependency_overrides[obter_sessao] = lambda: db
    monkeypatch.setattr(territorios, "vigentes", lambda d, a: [])
    monkeypatch.setattr(territorios.servico_fontes, "meta", painel.servico_fontes.meta)
    r = c.get("/api/v1/territorios/prioridades")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["dados"]["total"] == 3 and corpo["dados"]["itens"][0]["territorio_id"] == "ds-2"
    assert "Experimental" in corpo["meta"]["avisos"][0]
    assert corpo["meta"]["recorte"]["granularidade"] == "distrito"
    assert c.get("/api/v1/territorios/prioridades?horizonte_h=10").status_code == 422
    assert c.get("/api/v1/territorios/prioridades?distrito_id=ds-9").status_code == 422
    assert c.get("/api/v1/territorios/prioridades?nivel=rua").status_code == 422


def test_prioridades_tudo_insuficiente_explica(monkeypatch, servico):
    c = _cliente(monkeypatch)
    c.app.dependency_overrides[obter_sessao] = lambda: BancoFalso([("ds-3", "DS III")])
    monkeypatch.setattr(territorios, "vigentes", lambda d, a: [])
    corpo = c.get("/api/v1/territorios/prioridades").json()
    assert corpo["meta"]["dados_insuficientes"] is True
    assert "Não há dados suficientes" in corpo["dados"]["resumo"]
