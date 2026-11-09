"""Meteorologia observada e de modelo (migração 0021) com respostas REAIS gravadas em 06/11/2026 (fixtures/), sem
rede nem banco.

Onde a resposta real não trazia o caso (tudo zero na gravação, nenhum aviso de outro município), o teste altera um
campo da resposta real e diz qual; nenhuma resposta inteira é inventada.
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime

import pandas as pd
import pytest

from climasense.etl.conectores import apac, apac_previsao, open_meteo
from climasense.etl.conectores.base import FonteSemDados
from tests.unit.etl.test_conectores_chuva import Http, Resposta, _json, bronze, ctx

AGORA = datetime(2026, 11, 7, 1, 55, tzinfo=UTC)  # 22:55 de 06/11 no Recife


# ---------------------------------------------------------------------------------------------- APAC: chuva
def test_corpo_json_e_decodificado_como_utf8_mesmo_sem_charset():
    resposta = Resposta(conteudo='[{"estacao": "Torreão"}]'.encode())
    assert apac.json_utf8(resposta) == [{"estacao": "Torreão"}]


def _apac(cadastro=True):
    rotas = {"precipitacao_acumulada": Resposta(_json("apac_precipitacao_acumulada_2026-11-06.json"))}
    if cadastro:
        rotas["estacoes"] = Resposta(_json("apac_estacoes_2026-11-06.json"))
    c = apac.ConectorApacChuva(http=Http(rotas))
    registros = c.extrair(ctx(agora=AGORA))
    return c, c.transformar(bronze(registros), ctx(agora=AGORA)), registros


def test_apac_18_estacoes_nomes_reparados_e_passo_sem_valor_nao_vira_zero():
    c, leituras, registros = _apac()
    assert len(c.estacoes) == 18 and len(leituras) == 18 * len(apac.JANELAS)  # 18, não 19, em 06/11
    nomes = {e["nome"] for e in c.estacoes.values()}
    assert "[CEMADEN] Torreão" in nomes and "[CEMADEN] Morro da conceição" in nomes
    assert not any("�" in n or "Ã" in n for n in nomes)
    assert len(c.passos) == 18
    brega = next(
        p for p in c.passos if p["estacao_id"] == "apac-261160603G"
    )  # ultima_medicao = -1 (erro do sensor)
    assert brega["valor_mm"] is None
    pina = next(p for p in c.passos if p["estacao_id"] == "apac-261160617A")
    assert pina["valor_mm"] == 0.0  # zero medido continua zero
    assert pina["lida_em"] == datetime(2026, 11, 7, 1, 40, tzinfo=UTC)  # 22:40 local


def test_apac_cadastro_marca_estacao_sem_leitura_e_escolhe_o_registro_com_hora():
    c, _, registros = _apac()
    por = {d["codigo_fonte"]: d for d in c.cadastro}
    assert por["261160609A"]["status_dados"] == "observação"  # Imbiribeira: acento reparado
    assert por["261160614A"]["status_dados"] == "desatualizada" and por["261160614A"]["tempo_min"] == 878
    assert por["261160623A"]["nome"] == "[APAC] Sede"  # o outro cadastro [APAC] do mesmo código vem vazio
    assert por["261160617A"]["status_dados"] == "atualizada"
    assert sum(1 for r in registros if r.get("_endpoint") == "estacoes") == 48


def test_apac_cadastro_fora_do_ar_nao_derruba_a_chuva():
    c, leituras, _ = _apac(cadastro=False)
    assert len(c.passos) == 18 and c.cadastro == [] and c.cadastro_indisponivel is True
    assert len(leituras) == 18 * len(apac.JANELAS)


def test_corrigir_texto_nao_deixa_caractere_invalido():
    assert apac.corrigir_texto("TorreÃ£o") == "Torreão"  # UTF-8 lido como Latin-1
    assert apac.corrigir_texto("Dois Irm�os") == "Dois Irmãos"
    assert apac.corrigir_texto("Palavra � desconhecida") == "Palavra ? desconhecida"
    assert apac.corrigir_texto(None) == ""


# ------------------------------------------------------------------------- APAC: previsão, tendência e radar
def _prev(rotas=None, **alterar):
    base = {
        "previsao_municipio": Resposta(_json("apac_previsao_municipio_2026-11-06.json")),
        "tendencia_precipitacao": Resposta(_json("apac_tendencia_precipitacao_2026-11-06.json")),
        "radar_meteorologico": Resposta(_json("apac_radar_meteorologico_2026-11-06.json")),
    }
    base.update(rotas or {})
    c = apac_previsao.ConectorApacPrevisao(http=Http(base))
    registros = c.extrair(ctx(agora=AGORA))
    return c, c.transformar(bronze(registros), ctx(agora=AGORA))


def test_previsao_horaria_guarda_codigo_recebido_e_hora_em_utc():
    c, df = _prev()
    prev = df[df["alvo"] == "previsao"]
    assert len(prev) == 120 and set(prev["codigo_recebido"]) == {2612000}
    assert prev["hora_prevista"].min() == datetime(2026, 11, 6, 3, 0, tzinfo=UTC)  # 00:00 local
    assert prev["temperatura_c"].notna().all() and c.descartes == {}


def test_previsao_de_outro_municipio_e_descartada_inteira():
    # alteração do fixture real: o que a APAC devolve pelo código IBGE (2611606) é Pombos, com as coordenadas dele
    pombos = copy.deepcopy(_json("apac_previsao_municipio_2026-11-06.json"))
    for r in pombos:
        r.update(municipio="Pombos", codigo_municipio=2611606, latitude=-8.1369, longitude=-35.3939)
    c, df = _prev({"previsao_municipio": Resposta(pombos)})
    assert (df["alvo"] != "previsao").all()
    assert c.descartes["previsao_de_outro_municipio_ou_codigo_invalido"] == 120


@pytest.mark.parametrize(
    "campo",
    [{"codigo_municipio": 2611000}, {"latitude": -7.5}, {"municipio": "Olinda"}],
)
def test_previsao_valida_exige_nome_codigo_conhecido_e_coordenada_no_recife(campo):
    real = _json("apac_previsao_municipio_2026-11-06.json")[0]
    assert apac_previsao.previsao_valida(real)
    assert not apac_previsao.previsao_valida({**real, **campo})


def test_tendencia_so_metropolitana_e_radar_so_com_url_da_apac_sem_baixar_imagem():
    c, df = _prev()
    t = df[df["alvo"] == "tendencia"]
    assert len(t) == 5 and set(t["mesorregiao"]) == {"Metropolitana"}
    assert t.iloc[0]["atualizado_em"] == datetime(2026, 11, 6, 13, 0, 19, tzinfo=UTC)
    r = df[df["alvo"] == "radar"]
    assert len(r) == 10 and r["url_acumulado_1h"].str.startswith("https://barramento2.apac.pe.gov.br/").all()
    pedidos = [u for u, _ in c.http.pedidos]
    assert len(pedidos) == 3 and not any(u.endswith(".png") for u in pedidos)  # nenhuma imagem foi baixada


def test_radar_ignora_url_fora_do_dominio_da_apac():
    # alteração do fixture real: uma URL apontando para outro domínio e outra com http simples
    radar = copy.deepcopy(_json("apac_radar_meteorologico_2026-11-06.json"))
    radar[0]["acumulado_1h"] = "https://exemplo.invalido/x.png"
    radar[0]["acumulado_24h"] = "http://barramento2.apac.pe.gov.br/y.png"
    _, df = _prev({"radar_meteorologico": Resposta(radar)})
    primeira = df[df["alvo"] == "radar"].sort_values("data_referencia").iloc[-1]
    assert pd.isna(primeira["url_acumulado_1h"]) and pd.isna(primeira["url_acumulado_24h"])
    assert primeira["url_cappi_1km"].startswith("https://barramento2.apac.pe.gov.br/")


def test_rota_fora_do_ar_nao_derruba_as_outras_e_tudo_fora_do_ar_e_falha_explicada():
    c, df = _prev({"radar_meteorologico": Resposta(erro=RuntimeError("fora do ar"))})
    assert c.descartes == {"rota_indisponivel:radar": 1} and set(df["alvo"]) == {"previsao", "tendencia"}
    todas = {k: Resposta({"erro": "indisponível"}) for k in apac_previsao.ROTAS.values()}
    morto = apac_previsao.ConectorApacPrevisao(http=Http(todas))
    with pytest.raises(FonteSemDados):
        morto.extrair(ctx(agora=AGORA))


# ---------------------------------------------------------------------------------- Open-Meteo: solo e temperatura
def _solo(modo, resposta, alterar=None):
    corpo = _json(resposta)
    if alterar:
        corpo = alterar(copy.deepcopy(corpo))
    c = open_meteo.ConectorOpenMeteoSolo(http=Http({"open-meteo.com": Resposta(corpo)}))
    registros = c.extrair(ctx(modo=modo, agora=AGORA))
    return c, c.transformar(bronze(registros), ctx(modo=modo, agora=AGORA)), registros


def test_solo_previsao_tem_duas_camadas_por_distrito_e_nenhum_valor_medido():
    c, df, registros = _solo(None, "open_meteo_solo_previsao_2026-11-06.json")
    n = len(registros)  # um por distrito
    assert n >= 6 and len(df) == n * 2 * 120 and set(df["camada"]) == {"0_7cm", "7_28cm"}
    assert df["valor"].between(0, 1).all()
    assert c.fonte.tipo == "derivada" and c.id == "open-meteo-solo"
    pedido = c.http.pedidos[0]
    assert "api.open-meteo.com/v1/forecast" in pedido[0] and pedido[1]["past_days"] == 2


def test_solo_hora_sem_valor_e_valor_impossivel_ficam_de_fora_e_sao_contados():
    def alterar(corpo):  # alteração do fixture real: uma hora nula e um valor fora de 0 a 1 na camada rasa
        corpo["hourly"]["soil_moisture_0_to_7cm"][3] = None
        corpo["hourly"]["soil_moisture_0_to_7cm"][4] = 1.7
        return corpo

    c, df, registros = _solo(None, "open_meteo_solo_previsao_2026-11-06.json", alterar)
    n = len(registros)
    assert c.descartes == {"hora_sem_valor": n, "valor_fora_da_faixa": n}
    assert len(df) == n * 2 * 120 - 2 * n


def test_solo_historico_vira_media_diaria_e_dia_incompleto_nao_entra():
    c, df, registros = _solo("historico", "open_meteo_solo_historico_2026-10.json")
    n = len(registros)
    assert len(df) == n * 2 * 5 and (df["n_horas"] == 24).all()
    assert "archive-api" in c.http.pedidos[0][0]

    def sem_ultima_hora(corpo):  # alteração do fixture real: some a última hora do 5º dia
        for k in ("time", "soil_moisture_0_to_7cm", "soil_moisture_7_to_28cm"):
            corpo["hourly"][k] = corpo["hourly"][k][:-1]
        return corpo

    c2, df2, _ = _solo("historico", "open_meteo_solo_historico_2026-10.json", sem_ultima_hora)
    assert len(df2) == n * 2 * 4 and c2.descartes["dia_incompleto"] == n * 2


def test_solo_modo_desconhecido_falha():
    c = open_meteo.ConectorOpenMeteoSolo(http=Http({}))
    with pytest.raises(ValueError):
        c.extrair(ctx(modo="radar"))


def test_temperatura_e_previsao_de_modelo_nunca_medida():
    c = open_meteo.ConectorOpenMeteoTemperatura(
        http=Http({"open-meteo.com": Resposta(_json("open_meteo_temperatura_2026-11-06.json"))})
    )
    registros = c.extrair(ctx(agora=AGORA))
    df = c.transformar(bronze(registros), ctx(agora=AGORA))
    assert set(df["variavel"]) == {"temp_c"} and set(df["tipo"]) == {"prevista"}
    assert (df["emitido_em"] == AGORA).all() and df["horizonte_h"].min() == 0
    assert df["valor"].between(10, 45).all()
