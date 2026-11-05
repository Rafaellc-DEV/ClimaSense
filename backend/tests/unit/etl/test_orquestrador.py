"""Orquestração `etl atualizar` e o princípio “silver nasce do que foi lido de volta do Atlas” (sem redes reais)."""

import mongomock
import pandas as pd
import pytest

from climasense.etl import execucao, gold, orquestrador
from climasense.etl.conectores.base import Conector, ExecucaoCtx, FonteInfo


class _Conexao:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Engine:
    def connect(self):
        return _Conexao()


@pytest.fixture
def ambiente(monkeypatch):
    chamadas = []
    monkeypatch.setattr(execucao, "iniciar", lambda e, f: chamadas.append(("iniciar", f)) or f"id-{f}")
    monkeypatch.setattr(execucao, "concluir", lambda e, i, **kw: chamadas.append(("concluir", i, kw)))
    monkeypatch.setattr(gold, "verificar", lambda c: {"gold.chuva_diaria": 0})
    monkeypatch.setattr(orquestrador, "_recente", lambda e, f: False)
    return chamadas


def _ok(engine, mongo, config, fonte, eid, limite=None, modo=None):
    _ok.limites[(fonte, modo)] = limite
    return {"status": "sucesso", "lidos": 3, "gravados": 3, "descartados": 0, "erro": None}


_ok.limites = {}


def test_atualizar_roda_as_fontes_na_ordem_com_janela_movel_do_historico(ambiente):
    passos = orquestrador.atualizar(_Engine(), None, None, carregar_territorio=lambda: (89, 89), executar=_ok)
    assert [p.nome for p in passos] == [
        "territorio-oficial",
        "open-meteo-historico",
        "open-meteo-previsao",
        "open-meteo-mare",
        "apac-chuva",
        "apac-chuva (historico)",
        "alertas-oficiais",
        "recife-abrigos (ativos)",
        "infodengue",
        "recife-alagamento",
        "recife-abrigos",
        "sinan-leptospirose",
        "recife-arboviroses",
        "verificar-gold",
    ]
    assert all(p.status == "sucesso" for p in passos)
    assert _ok.limites[("open-meteo-historico", None)] == orquestrador.JANELA_HISTORICO_DIAS
    assert _ok.limites[("apac-chuva", "historico")] == orquestrador.JANELA_APAC_HISTORICO_MESES


def test_tempo_real_roda_so_as_fontes_rapidas(ambiente):
    passos = orquestrador.atualizar(_Engine(), None, None, executar=_ok, ordem=orquestrador.ORDEM_TEMPO_REAL)
    assert [p.nome for p in passos] == [
        "apac-chuva",
        "alertas-oficiais",
        "recife-abrigos (ativos)",
        "verificar-gold",
    ]


def test_semanal_roda_so_a_saude(ambiente):
    passos = orquestrador.atualizar(
        _Engine(), None, None, forcar=True, executar=_ok, ordem=orquestrador.ORDEM_SEMANAL
    )
    assert [p.nome for p in passos] == ["infodengue", "sinan-leptospirose", "verificar-gold"]


def test_falha_de_uma_fonte_nao_impede_as_demais_mas_aparece_no_resumo(ambiente):
    def executar(engine, mongo, config, fonte, eid, limite=None, modo=None):
        if fonte == "open-meteo-previsao":
            return {
                "status": "falha",
                "lidos": 0,
                "gravados": 0,
                "descartados": 0,
                "erro": "A fonte não respondeu.",
            }
        return _ok(engine, mongo, config, fonte, eid, limite, modo)

    passos = orquestrador.atualizar(_Engine(), None, None, executar=executar)
    estados = {p.nome: p.status for p in passos}
    assert estados["open-meteo-previsao"] == "falha" and estados["open-meteo-mare"] == "sucesso"
    assert "não respondeu" in next(p.detalhe for p in passos if p.nome == "open-meteo-previsao")


def test_conjuntos_estaticos_recentes_sao_pulados_sem_forcar(ambiente, monkeypatch):
    monkeypatch.setattr(orquestrador, "_recente", lambda e, f: True)
    estado = {p.nome: p.status for p in orquestrador.atualizar(_Engine(), None, None, executar=_ok)}
    assert estado["recife-alagamento"] == "pulado" and estado["recife-abrigos"] == "pulado"
    assert estado["sinan-leptospirose"] == "pulado" and estado["recife-arboviroses"] == "pulado"
    assert estado["infodengue"] == "sucesso"  # muda toda semana: roda sempre
    assert estado["apac-chuva"] == "sucesso" and estado["recife-abrigos (ativos)"] == "sucesso"
    estado = {
        p.nome: p.status for p in orquestrador.atualizar(_Engine(), None, None, forcar=True, executar=_ok)
    }
    assert estado["recife-alagamento"] == "sucesso"


def test_gold_divergente_e_territorio_com_erro_geram_falha_sem_vazar_detalhes(ambiente, monkeypatch):
    monkeypatch.setattr(gold, "verificar", lambda c: {"gold.chuva_diaria": 2})

    def quebra():
        raise ConnectionError("mongodb+srv://" + "usuario" + ":segredo@cluster")

    passos = orquestrador.atualizar(_Engine(), None, None, carregar_territorio=quebra, executar=_ok)
    assert passos[0].status == "falha" and "segredo" not in passos[0].detalhe
    assert passos[-1].status == "falha"
    erro = [c for c in ambiente if c[0] == "concluir"][0][2]["erro"]
    assert "segredo" not in erro


class _Teste(Conector):
    id = "teste"
    fonte = FonteInfo("t", "t", "https://t", "observada")

    def __init__(self):
        super().__init__()
        self.visto = None

    def extrair(self, ctx):
        return [{"a": 1}, {"a": 2}]

    def transformar(self, bruto, ctx):
        return bruto

    def gravar_silver(self, df, ctx):
        self.visto = df
        return len(df)


def test_silver_e_construida_a_partir_da_leitura_do_atlas_e_so_do_lote_atual():
    mongo = mongomock.MongoClient()
    ctx = ExecucaoCtx("exec-2", None, mongo, None, None)
    conector = _Teste()
    mongo["bronze"]["teste"].insert_one({"a": 99, "_execucao_id": "exec-1", "_fonte": "teste"})
    r = conector.executar(ctx)
    assert r.lidos == 2 and sorted(conector.visto["a"]) == [1, 2]  # veio do Atlas, sem o lote antigo
    assert mongo["bronze"]["teste"].count_documents({}) == 3  # bronze cumulativa
    assert pd.Series(conector.visto.columns).tolist() == ["a"]
