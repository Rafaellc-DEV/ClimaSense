"""Meteorologia observada (migração 0021) de ponta a ponta no Postgres de teste, com as respostas REAIS gravadas em
06/11/2026. Tudo roda dentro de uma transação desfeita no fim.

A resposta real do dia só trazia zeros; onde o teste precisa de chuva, ele altera `ultima_medicao` e `72_horas` de
estações reais e diz isso no próprio teste."""

from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from climasense.etl import execucao, gold
from climasense.etl.conectores.apac import ConectorApacChuva
from climasense.etl.conectores.apac_previsao import ConectorApacPrevisao
from climasense.etl.conectores.open_meteo import ConectorOpenMeteoSolo
from tests.conftest import precisa_postgres
from tests.integration.test_etl_chuva import ambiente, rodar  # noqa: F401 — fixture compartilhada
from tests.unit.etl.test_conectores_chuva import Http, Resposta, _json

pytestmark = [precisa_postgres, pytest.mark.integracao]
AGORA = datetime(2026, 11, 7, 1, 55, tzinfo=UTC)  # 22:55 de 06/11 no Recife


def _http_apac(prec):
    return Http(
        {
            "precipitacao_acumulada": Resposta(prec),
            "estacoes": Resposta(_json("apac_estacoes_2026-11-06.json")),
        }
    )


def _linhas(engine, sql, **p):
    return engine.c.execute(text(sql), p).mappings().all()


def test_chuva_72h_por_distrito_serie_horaria_e_estacoes_sem_leitura(ambiente):  # noqa: F811
    engine, mongo, config, _db = ambiente
    prec = _json("apac_precipitacao_acumulada_2026-11-06.json")
    rodar(engine, mongo, config, ConectorApacChuva(http=_http_apac(prec)), agora=AGORA)

    # 2ª coleta: ALTERAÇÃO da resposta real. A Pina (22:40) lê 1,5 mm às 22:50 e o acumulado de 72 h dela vai a 12 mm;
    # a Barreira lê de novo às 22:20 com 72 h = 40 mm (uma leitura com a mesma hora nunca se repete na silver).
    seg = copy.deepcopy(prec)
    for r in seg:
        if r["codigo_estacao"] == "261160617A":
            r.update(data_hora_ultima_leitura="2026-11-06 22:50:00", ultima_medicao=1.5, **{"72_horas": 12.0})
        if r["codigo_estacao"] == "261160604G":
            r.update(data_hora_ultima_leitura="2026-11-06 22:20:00", **{"72_horas": 40.0})
    rodar(engine, mongo, config, ConectorApacChuva(http=_http_apac(seg)), agora=AGORA + timedelta(minutes=10))

    # --- 72 h por distrito: só leitura recente; distrito sem pluviômetro não herda do Recife
    ds = {
        r["territorio_id"]: r
        for r in _linhas(engine, "select * from gold.chuva_obs_72h_distrito where nivel = 'distrito'")
    }
    assert len(ds) >= 6
    assert {r["status"] for r in ds.values()} >= {"com_leitura", "sem_pluviometro"}
    for r in ds.values():
        if r["status"] == "sem_pluviometro":
            assert r["chuva_72h_max_mm"] is None and r["n_estacoes"] == 0 and r["estacoes"] == []
        if r["status"] == "com_leitura":
            assert r["chuva_72h_max_mm"] is not None and r["n_com_leitura"] > 0 and r["lida_em"] is not None
        assert r["n_com_leitura"] + r["n_sem_leitura"] == r["n_estacoes"]
    pina = _linhas(
        engine, "select distrito_id from gold.estacoes_chuva_status where estacao_id = 'apac-261160617A'"
    )[0]
    assert ds[pina["distrito_id"]]["chuva_72h_max_mm"] >= 12.0
    barreira = _linhas(
        engine, "select distrito_id from gold.estacoes_chuva_status where estacao_id = 'apac-261160604G'"
    )
    assert ds[barreira[0]["distrito_id"]]["chuva_72h_max_mm"] >= 40.0
    municipio = _linhas(engine, "select * from gold.chuva_obs_72h_distrito where nivel = 'municipio'")[0]
    assert municipio["chuva_72h_max_mm"] == 40.0 and municipio["n_estacoes"] == 18
    assert municipio["n_com_leitura"] == 15 and municipio["n_sem_leitura"] == 3  # 3 estações velhas em 06/11

    # --- estação sem leitura marcada com o status_dados do cadastro da APAC
    est = {r["estacao_id"]: r for r in _linhas(engine, "select * from gold.estacoes_chuva_status")}
    assert est["apac-261160609A"]["situacao"] == "leitura_antiga"  # Imbiribeira, última leitura às 13:10
    assert est["apac-261160609A"]["status_dados"] == "observação"
    assert (
        est["apac-261160617A"]["situacao"] == "com_leitura"
        and est["apac-261160617A"]["status_dados"] == "atualizada"
    )
    assert sum(1 for e in est.values() if e["situacao"] != "com_leitura") == 3

    # --- série horária: soma do que chegou na hora (2 leituras da Pina: 0 + 1,5), com hora e estação guardadas
    h = _linhas(
        engine,
        "select * from gold.chuva_obs_hora_distrito where territorio_id = :d and chuva_max_mm = 1.5",
        d=pina["distrito_id"],
    )
    assert len(h) == 1 and "apac-261160617A" in h[0]["estacoes"]
    assert h[0]["hora_inicio"] == datetime(
        2026, 11, 7, 1, 0, tzinfo=UTC
    )  # hora 22 local; leituras 22:40 e 22:50
    assert h[0]["n_completas"] == 0 and h[0]["n_com_leitura"] >= 1  # só 2 leituras na hora: mínimo medido
    assert h[0]["primeira_leitura_em"] < h[0]["ultima_leitura_em"]
    # leitura sem valor (ultima_medicao = -1, Brega e Chique) não vira zero: nenhuma linha de passo com 0 para ela
    brega = _linhas(
        engine, "select valor_mm from silver.apac_chuva_passos where estacao_id = 'apac-261160603G'"
    )
    assert [b["valor_mm"] for b in brega] == [None]
    # zero medido continua zero
    zero = _linhas(
        engine, "select valor_mm from silver.apac_chuva_passos where estacao_id = 'apac-261160604G'"
    )
    assert [z["valor_mm"] for z in zero] == [0.0, 0.0]  # 22:10 e 22:20
    # 2 coletas, 18 estações, 2 leituras novas (Pina 22:50 e Barreira 22:20): leitura repetida não duplica
    assert _linhas(engine, "select count(*) as n from silver.apac_chuva_passos")[0]["n"] == 20

    # --- tudo reproduzível a partir da silver
    assert gold.verificar(engine.c) == {t: 0 for t in gold.VERIFICADAS}


def test_sem_nenhuma_coleta_a_gold_fica_vazia_e_nunca_zero(ambiente):  # noqa: F811
    engine, *_ = ambiente
    gold.recalcular(engine.c, gold.TABELAS_CHUVA_OBS)
    for tabela in ("chuva_obs_hora_distrito", "chuva_obs_72h_distrito", "estacoes_chuva_status"):
        assert _linhas(engine, f"select count(*) as n from gold.{tabela}")[0]["n"] == 0  # noqa: S608
    assert gold.verificar(engine.c)["gold.chuva_obs_72h_distrito"] == 0


def test_previsao_tendencia_e_radar_ficam_com_fonte_e_hora(ambiente):  # noqa: F811
    engine, mongo, config, _db = ambiente
    http = Http(
        {
            "previsao_municipio": Resposta(_json("apac_previsao_municipio_2026-11-06.json")),
            "tendencia_precipitacao": Resposta(_json("apac_tendencia_precipitacao_2026-11-06.json")),
            "radar_meteorologico": Resposta(_json("apac_radar_meteorologico_2026-11-06.json")),
        }
    )
    r = rodar(engine, mongo, config, ConectorApacPrevisao(http=http), agora=AGORA)
    assert r.gravados == 120 + 5 + 10 and r.descartados == 0
    rodar(engine, mongo, config, ConectorApacPrevisao(http=http), agora=AGORA + timedelta(minutes=10))
    n = lambda t: _linhas(engine, f"select count(*) as n from silver.{t}")[0]["n"]  # noqa: E731, S608
    assert (n("apac_previsao_horaria"), n("apac_tendencia_chuva"), n("apac_radar")) == (120, 5, 10)  # upsert
    assert mongo["bronze"]["apac_previsao"].count_documents({}) == 2 * (120 + 35 + 10)  # bronze acumulativa
    radar = _linhas(engine, "select * from silver.apac_radar order by data_referencia desc")[0]
    assert radar["data_referencia"] == datetime(2026, 11, 7, 1, 55, tzinfo=UTC)
    assert (
        radar["url_acumulado_1h"].startswith("https://barramento2.apac.pe.gov.br/") and radar["coletado_em"]
    )
    assert (
        _linhas(engine, "select distinct codigo_recebido from silver.apac_previsao_horaria")[0][
            "codigo_recebido"
        ]
        == 2612000
    )


def _classe(p):
    return "seco" if p < 25 else "normal" if p < 75 else "umido" if p < 90 else "muito_umido"


def test_solo_modelo_percentil_do_proprio_ponto_so_com_historico_suficiente(ambiente):  # noqa: F811
    engine, mongo, config, _db = ambiente
    http = Http({"open-meteo.com": Resposta(_json("open_meteo_solo_previsao_2026-11-06.json"))})
    rodar(engine, mongo, config, ConectorOpenMeteoSolo(http=http), agora=AGORA)

    # só com o histórico curto real (5 dias) não há classe: Dados insuficientes, nunca um valor inventado
    hist = Http({"open-meteo.com": Resposta(_json("open_meteo_solo_historico_2026-10.json"))})
    rodar(engine, mongo, config, ConectorOpenMeteoSolo(http=hist), modo="historico", agora=AGORA)
    linhas = _linhas(engine, "select * from gold.solo_modelo_distrito")
    assert linhas and all(
        r["classe"] is None and r["percentil"] is None and r["n_historico_dias"] == 5 for r in linhas
    )
    assert {(r["natureza"], r["selo"]) for r in linhas} == {("modelo", "experimental")}

    # DADO DE TESTE: 400 dias de histórico diário sintético (rampa de 0,10 a 0,40) para um ponto, só aqui no teste
    eid = execucao.iniciar(engine, "open-meteo-solo")
    ponto = linhas[0]["territorio_id"]
    engine.c.execute(text("delete from silver.solo_modelo_diario where territorio_id = :t"), {"t": ponto})
    engine.c.execute(
        text(
            "insert into silver.solo_modelo_diario (territorio_id, camada, dia, media_m3m3, n_horas, coletado_em, "
            "execucao_id) select :t, c.camada, date '2025-01-01' + g, 0.10 + 0.30 * g / 399.0, 24, now(), cast(:e as uuid) "
            "from generate_series(0, 399) g cross join (values ('0_7cm'), ('7_28cm')) as c(camada)"
        ),
        {"t": ponto, "e": eid},
    )
    gold.recalcular(engine.c, gold.TABELAS_SOLO)
    atual = {
        r["camada"]: r
        for r in _linhas(engine, "select * from gold.solo_modelo_distrito where territorio_id = :t", t=ponto)
    }
    for camada, r in atual.items():
        assert r["n_historico_dias"] == 400 and r["n_horas"] == 24 and r["percentil"] is not None
        esperado = _quanto_no_historico(r["valor_24h_m3m3"])
        assert r["percentil"] == pytest.approx(esperado, abs=0.1)
        assert r["classe"] == _classe(r["percentil"]), camada
        assert r["p25_m3m3"] < r["p75_m3m3"] < r["p90_m3m3"]
    assert gold.verificar(engine.c)["gold.solo_modelo_distrito"] == 0


def _quanto_no_historico(valor):
    """Percentil esperado da rampa 0,10 + 0,30 g/399 (g = 0..399) para o valor dado."""
    dias = sum(1 for g in range(400) if 0.10 + 0.30 * g / 399.0 <= valor)
    return round(100.0 * dias / 400, 1)
