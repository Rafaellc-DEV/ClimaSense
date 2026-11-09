"""Conectores `apac-rios` e `apac-reservatorios` com respostas REAIS gravadas em 06/11/2026 (fixtures/), sem rede nem
banco. Onde um caso não existia no dia (data futura, texto quebrado, nível alto), o teste altera um campo da
resposta real e diz qual (ALTERADO); nenhuma resposta inteira é inventada."""

from __future__ import annotations

import copy
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest
import requests

from climasense.etl.conectores import CONECTORES, IMPLEMENTADOS, MODOS, apac_reservatorios, apac_rios
from climasense.etl.conectores.base import ExecucaoCtx, FonteSemDados
from tests.unit.etl.test_conectores_chuva import Http, Resposta, _json, bronze

FIX = Path(__file__).parent / "fixtures"
AGORA = datetime(2026, 11, 7, 1, 58, tzinfo=UTC)  # 22:58 de 06/11 no Recife (hora da gravação)
SEM_LEITURA = ("39170000", "39189560")  # lista vazia na resposta real: estação cadastrada sem dado recente


def ctx(modo=None, agora=AGORA, limite=None):
    return ExecucaoCtx("exec-1", None, None, None, agora, limite, modo)


def _historico(cod: str):
    arquivo = FIX / f"apac_historico_rios_{cod}_2026-11-06.json"
    return _json(arquivo.name) if arquivo.exists() else []  # as duas estações sem dado voltaram []


def _rotas(historico=None, cadastro=None, ana=None):
    def por_estacao(params):
        cod = params["cod_estacao"]
        corpo = historico(cod) if historico else _historico(cod)
        if isinstance(corpo, BaseException):
            raise corpo
        return Resposta(corpo)

    ana_resp = Resposta(conteudo=(FIX / "ana_dados_39187800_2026-11-06.xml").read_bytes())
    return {
        "estacoes_rios": Resposta(
            cadastro if cadastro is not None else _json("apac_estacoes_rios_2026-11-06.json")
        ),
        "historico_rios": por_estacao,
        "ServiceANA.asmx": ana if ana is not None else ana_resp,
    }


def _rodar(rotas=None, modo=None, limite=None):
    http = Http(rotas or _rotas())
    c = apac_rios.ConectorApacRios(http=http)
    registros = c.extrair(ctx(modo, limite=limite))
    return c, http, registros, c.transformar(bronze(registros), ctx(modo, limite=limite))


# ------------------------------------------------------------------------------------------ registro
def test_conectores_de_hidrologia_estao_registrados_como_implementados():
    for fid, classe in (
        ("apac-rios", apac_rios.ConectorApacRios),
        ("apac-reservatorios", apac_reservatorios.ConectorApacReservatorios),
    ):
        assert CONECTORES[fid] is classe and fid in IMPLEMENTADOS and classe.id == fid
    assert MODOS["apac-rios"] == ("24h", "72h")


# ------------------------------------------------------------------------------------------ rios: parser
def test_rios_cadastro_leituras_e_limiares_reais_das_oito_estacoes():
    c, http, registros, df = _rodar()
    assert set(c.estacoes) == set(apac_rios.ESTACOES_INICIAIS)  # Amaraji (fora da lista) ficou de fora
    sao_lourenco = c.estacoes["39187800"]
    assert sao_lourenco["rio"] == "RIO CAPIBARIBE" and sao_lourenco["bacia"] == "Capibaribe"
    assert sao_lourenco["nome"] == "SÃO LOURENÇO DA MATA (ANA/SGB)" and "Recife" in sao_lourenco["municipios"]
    assert sao_lourenco["inclui_recife"] is True and sao_lourenco["codigos_municipio"][1] == "2611606"
    assert c.estacoes["39150010"]["inclui_recife"] is False
    assert c.estacoes["260790119"]["bacia"] == "GL2" and c.estacoes["39170000"]["rio"] == "RIO TAPACURÁ"
    # 6 estações com 4 pontos reais da APAC + 4 da ANA
    assert len(df) == 6 * 4 + 4 and set(df["fonte"]) == {"apac", "ana"}
    ultima = (
        df[(df["estacao_codigo"] == "39187800") & (df["fonte"] == "apac")].sort_values("lida_em").iloc[-1]
    )
    assert ultima["lida_em"] == datetime(2026, 11, 5, 19, 15, tzinfo=UTC)  # 16:15 no Recife (UTC−3)
    assert ultima["nivel_cm"] == 179.0
    assert (ultima["pre_alerta_cm"], ultima["alerta_cm"], ultima["enchente_cm"]) == (250, 300, 400)
    assert ultima["alerta_pcd"] == "N" and ultima["recente"] == 0
    paudalho = df[df["estacao_codigo"] == "39150010"].iloc[-1]
    assert (paudalho["nivel_cm"], paudalho["pre_alerta_cm"]) == (189.0, 300)
    duas_unas = df[df["estacao_codigo"] == "260790119"].sort_values("lida_em").iloc[-1]
    assert duas_unas["nivel_cm"] == 138.8 and duas_unas["enchente_cm"] == 330


def test_rios_estacao_com_lista_vazia_fica_sem_leitura_e_nunca_vira_zero():
    c, _, _, df = _rodar()
    assert not set(SEM_LEITURA) & set(df["estacao_codigo"])  # ausente ≠ 0 (RN-02)
    assert all(c.avisos[f"apac_sem_leituras_{cod}"] == 1 for cod in SEM_LEITURA)
    assert set(SEM_LEITURA) <= set(
        c.estacoes
    )  # continuam no cadastro, para a gold mostrar "Dados insuficientes"


def test_rios_ana_traz_so_nivel_e_vazao_sem_limiares():
    _, _, _, df = _rodar()
    ana = df[df["fonte"] == "ana"].sort_values("lida_em")
    assert set(ana["estacao_codigo"]) == {"39187800"}
    assert ana["pre_alerta_cm"].isna().all() and (ana["vazao_m3s"] == 1.19).all()
    assert ana["lida_em"].iloc[-1] == datetime(
        2026, 11, 6, 18, 15, tzinfo=UTC
    )  # 15:15 no Recife; espaço final ignorado
    assert ana["nivel_cm"].iloc[-1] == 177.0


def test_rios_periodo_72h_vai_na_consulta_e_modo_desconhecido_e_recusado():
    _, http, _, _ = _rodar(modo="72h")
    periodos = {p["periodo"] for u, p in http.pedidos if "historico_rios" in u}
    assert periodos == {"72h"}
    with pytest.raises(ValueError, match="Modo desconhecido"):
        apac_rios.ConectorApacRios(http=Http(_rotas())).extrair(ctx("7d"))
    _, http24, _, _ = _rodar()
    assert {p["periodo"] for u, p in http24.pedidos if "historico_rios" in u} == {"24h"}


# ------------------------------------------------------------------------------------------ rios: limiares
@pytest.mark.parametrize(
    ("nivel", "classe"),
    [
        (0, "abaixo_pre_alerta"),  # zero medido é medida
        (179, "abaixo_pre_alerta"),
        (249.99, "abaixo_pre_alerta"),
        (250, "pre_alerta"),  # atingiu o limiar = está na classe
        (299, "pre_alerta"),
        (300, "alerta"),
        (399.9, "alerta"),
        (400, "enchente"),
        (900, "enchente"),
        (None, "dados_insuficientes"),
        (-1, "dados_insuficientes"),  # negativo é código de erro do sensor
        ("-", "dados_insuficientes"),
    ],
)
def test_classe_do_rio_pelos_limiares_oficiais_da_estacao(nivel, classe):
    assert apac_rios.classificar_nivel(nivel, 250, 300, 400) == classe


@pytest.mark.parametrize(
    "lim",
    [(None, 300, 400), (300, 250, 400), (250, 250, 400), (0, 300, 400), ("-", "-", "-"), (250, 300, None)],
)
def test_limiares_incompletos_ou_fora_de_ordem_deixam_a_estacao_sem_classe(lim):
    assert apac_rios.limiares(*lim) is None
    assert apac_rios.classificar_nivel(179, *lim) == "dados_insuficientes"


def test_limiares_invalidos_na_resposta_ficam_nulos_e_sao_avisados():
    historico = _historico("39187800")
    historico[-1] = {**historico[-1], "nivel_alerta": "100"}  # ALTERADO: alerta abaixo do pré-alerta (250)
    c, _, _, df = _rodar(_rotas(historico=lambda cod: historico if cod == "39187800" else _historico(cod)))
    ruim = df[(df["fonte"] == "apac") & (df["estacao_codigo"] == "39187800") & df["pre_alerta_cm"].isna()]
    assert len(ruim) == 1 and ruim.iloc[0]["nivel_cm"] == 179.0  # o nível fica, a classe não sai
    assert c.avisos["limiares_invalidos"] == 1


# ------------------------------------------------------------------------------------------ rios: descartes
def test_rios_leitura_com_data_futura_e_descartada():
    historico = _historico("39187800")
    historico[-1] = {**historico[-1], "data_hora": "2026-11-12 16:15:00"}  # ALTERADO: data futura
    c, _, _, df = _rodar(_rotas(historico=lambda cod: historico if cod == "39187800" else _historico(cod)))
    assert c.descartes == {"leitura_no_futuro": 1}
    assert datetime(2026, 11, 12, tzinfo=UTC) > df["lida_em"].max()
    # poucos minutos de relógio adiantado não contam como futuro
    limite = {
        **_historico("39187800")[-1],
        "data_hora": "2026-11-06 23:05:00",
    }  # 23:05 local, 7 min depois de AGORA
    c2, _, _, df2 = _rodar(_rotas(historico=lambda cod: [limite] if cod == "39187800" else _historico(cod)))
    assert c2.descartes == {} and (df2["lida_em"] == datetime(2026, 11, 7, 2, 5, tzinfo=UTC)).any()


def test_rios_nivel_ausente_ou_negativo_e_descartado_sem_virar_zero():
    historico = _historico("39187800")
    historico[0] = {**historico[0], "nivel_atual": "-"}  # ALTERADO
    historico[1] = {**historico[1], "nivel_atual": "-9999"}  # ALTERADO: código de erro do sensor
    historico[2] = {**historico[2], "data_hora": ""}  # ALTERADO
    c, _, _, df = _rodar(_rotas(historico=lambda cod: historico if cod == "39187800" else _historico(cod)))
    assert c.descartes == {"nivel_ausente": 2, "sem_hora_da_leitura": 1}
    assert len(df[(df["estacao_codigo"] == "39187800") & (df["fonte"] == "apac")]) == 1


def test_rios_estacao_fora_do_cadastro_e_descartada():
    cadastro = [e for e in _json("apac_estacoes_rios_2026-11-06.json") if e["cod_estacao"] != "39150010"]
    c, _, _, df = _rodar(_rotas(cadastro=cadastro))
    assert c.descartes == {"estacao_fora_do_cadastro": 1} and "39150010" not in set(df["estacao_codigo"])


# ------------------------------------------------------------------------------------------ rios: acentos
def test_corrigir_texto_conserta_utf8_lido_como_latin1_e_acusa_bytes_perdidos():
    assert apac_rios.corrigir_texto("SÃ£o LourenÃ§o da Mata") == "São Lourenço da Mata"
    assert apac_rios.corrigir_texto("VitÃ³ria de Santo AntÃ£o") == "Vitória de Santo Antão"
    assert apac_rios.corrigir_texto("São Lourenço da Mata") == "São Lourenço da Mata"  # íntegro: não mexe
    assert apac_rios.corrigir_texto("  RIO   CAPIBARIBE ") == "RIO CAPIBARIBE"
    assert apac_rios.corrigir_texto(None) is None and apac_rios.corrigir_texto("  ") is None
    perdido = apac_rios.corrigir_texto("S�o Louren�o")
    assert apac_rios.texto_quebrado(perdido) and not apac_rios.texto_quebrado("São Lourenço")


def test_rios_texto_com_bytes_perdidos_usa_o_nome_canonico_da_estacao():
    cadastro = copy.deepcopy(_json("apac_estacoes_rios_2026-11-06.json"))
    for e in cadastro:
        if e["cod_estacao"] == "39187800":  # ALTERADO: reproduz o texto quebrado visto na pesquisa
            e["nome_estacao"] = "S�O LOUREN�O DA MATA (ANA/SGB)"
            e["municipios"] = "Camaragibe, Recife, S�o Louren�o da Mata"
        if e["cod_estacao"] == "39170000":  # ALTERADO: UTF-8 lido como Latin-1
            e["nome_rio"] = "RIO TAPACURÃ\x81"
    c, _, _, _ = _rodar(_rotas(cadastro=cadastro))
    assert c.estacoes["39187800"]["nome"] == "São Lourenço da Mata (ANA/SGB)"
    assert c.estacoes["39187800"]["municipios"] == "Camaragibe, Recife, São Lourenço da Mata"
    assert "�" not in str(c.estacoes) and c.estacoes["39170000"]["rio"] != "RIO TAPACURÃ\x81"


# ------------------------------------------------------------------------------------------ rios: falhas
def test_rios_erro_da_apac_com_http_200_vira_falha_explicada():
    rotas = _rotas()
    rotas["estacoes_rios"] = Resposta({"erro": "Serviço indisponível"})
    with pytest.raises(FonteSemDados, match="Serviço indisponível"):
        apac_rios.ConectorApacRios(http=Http(rotas)).extrair(ctx())
    rotas = _rotas(historico=lambda cod: Resposta({"erro": "sem dados"}).corpo)
    with pytest.raises(FonteSemDados, match="nenhuma estação"):
        apac_rios.ConectorApacRios(http=Http(rotas)).extrair(ctx())


def test_rios_falha_em_uma_estacao_segue_com_as_outras_e_rotula_amostra():
    def historico(cod):
        return requests.ConnectionError("sem rede") if cod == "39150010" else _historico(cod)

    c, _, registros, df = _rodar(_rotas(historico=historico))
    assert "39150010" not in set(df["estacao_codigo"]) and c.avisos["apac_falhou"] == 1
    assert c.amostra and all(r.get("amostra") for r in registros)  # RN-10


def test_rios_ana_fora_do_ar_nao_derruba_a_execucao():
    def fora(params):
        raise requests.ConnectionError("ana fora")

    c, _, registros, df = _rodar(_rotas(ana=fora))
    assert set(df["fonte"]) == {"apac"} and c.avisos["ana_falhou"] == 1
    assert next(r for r in registros if r["_origem"] == "ana_telemetria")["erro"] == "ConnectionError"


def test_rios_xml_da_ana_com_dtd_e_recusado():
    malicioso = Resposta(conteudo=b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><DataTable/>')
    c, _, _, df = _rodar(_rotas(ana=malicioso))
    assert set(df["fonte"]) == {"apac"} and c.avisos["ana_falhou"] == 1


def test_parse_ana_le_o_dataset_real():
    linhas = apac_rios.parse_ana((FIX / "ana_dados_39187800_2026-11-06.xml").read_bytes())
    assert len(linhas) == 4
    assert linhas[0] == {
        "CodEstacao": "39187800",
        "DataHora": "2026-11-06 15:15:00",
        "Vazao": "1.19",
        "Nivel": "177.00",
        "Chuva": "0.00",
    }


def test_rios_amostra_com_limite_de_estacoes_e_rotulada():
    c, _, registros, df = _rodar(limite=2)
    assert c.amostra and set(df["estacao_codigo"]) == {"39187800", "39150010"}
    assert all(r.get("amostra") and r["n_estacoes"] == 2 for r in registros)
    _, _, completos, _ = _rodar()
    assert not any(r.get("amostra") for r in completos)


# ------------------------------------------------------------------------------------------ reservatórios
def _reservatorios(corpo=None):
    return Http(
        {
            "reservatorio": Resposta(
                corpo if corpo is not None else _json("apac_reservatorio_capibaribe_2026-11-06.json")
            )
        }
    )


def _rodar_reservatorios(corpo=None):
    c = apac_reservatorios.ConectorApacReservatorios(http=_reservatorios(corpo))
    registros = c.extrair(ctx())
    return c, registros, c.transformar(bronze(registros), ctx())


def test_reservatorios_guarda_so_os_quatro_de_interesse_com_status_oficial():
    c, registros, df = _rodar_reservatorios()
    assert len(registros) == 14  # a bronze guarda a bacia inteira
    assert set(df["codigo_estacao"]) == set(apac_reservatorios.RESERVATORIOS)
    por_cod = df.set_index("codigo_estacao")
    assert (
        por_cod.loc[39175000, "volume_pct"] == 95.36 and por_cod.loc[39175000, "status"] == "ENTRE 80% e 100%"
    )
    assert por_cod.loc[39151000, "volume_pct"] == 38.2 and por_cod.loc[39145550, "volume_pct"] == 24.12
    assert por_cod.loc[39187900, "status"] == "VERTENDO" and por_cod.loc[39187900, "volume_pct"] == 100.2
    assert por_cod.loc[39175000, "cota_m"] == 102.48
    assert (
        c.cadastro[39175000]["nome"] == "Tapacurá"
        and c.cadastro[39175000]["municipio"] == "São Lourenço da Mata"
    )
    assert c.cadastro[39175000]["capacidade_m3"] == 104870609
    assert c.descartes == {}


def test_reservatorios_leitura_com_data_futura_e_descartada():
    corpo = copy.deepcopy(_json("apac_reservatorio_capibaribe_2026-11-06.json"))
    for r in corpo:
        if r["codigo_estacao"] == 39151000:  # ALTERADO: data futura (como a vista no histórico da APAC)
            r["data_leitura_cota_atual"] = "2026-11-12"
    c, _, df = _rodar_reservatorios(corpo)
    assert 39151000 not in set(df["codigo_estacao"]) and c.descartes["leitura_no_futuro"] == 1


def test_reservatorios_acentos_quebrados_nao_atrapalham_o_casamento_por_codigo():
    corpo = copy.deepcopy(_json("apac_reservatorio_capibaribe_2026-11-06.json"))
    for r in corpo:
        if r["codigo_estacao"] == 39175000:  # ALTERADO: bytes perdidos como na pesquisa
            r["municipio"], r["reservatorio"] = "S�o Louren�o da Mata", "TAPACUR�"
        if r["codigo_estacao"] == 39187900:  # ALTERADO: UTF-8 lido como Latin-1
            r["municipio"] = "SÃ£o LourenÃ§o da Mata"
    c, _, df = _rodar_reservatorios(corpo)
    assert 39175000 in set(df["codigo_estacao"])
    assert c.cadastro[39175000]["municipio"] == "São Lourenço da Mata"
    assert c.cadastro[39187900]["municipio"] == "São Lourenço da Mata"


def test_reservatorios_ausente_na_resposta_e_contado_e_erro_vira_falha_explicada():
    corpo = [
        r for r in _json("apac_reservatorio_capibaribe_2026-11-06.json") if r["codigo_estacao"] != 39151000
    ]
    c, _, df = _rodar_reservatorios(corpo)
    assert len(df) == 3 and c.descartes == {"reservatorio_ausente_na_resposta": 1}
    with pytest.raises(FonteSemDados, match="sem dados"):
        apac_reservatorios.ConectorApacReservatorios(http=_reservatorios({"erro": "x"})).extrair(ctx())
    with pytest.raises(FonteSemDados):
        apac_reservatorios.ConectorApacReservatorios(http=_reservatorios([])).extrair(ctx())


def test_reservatorios_sem_data_e_descartado():
    corpo = copy.deepcopy(_json("apac_reservatorio_capibaribe_2026-11-06.json"))
    for r in corpo:
        if r["codigo_estacao"] == 39145550:
            r["data_leitura_cota_atual"] = None  # ALTERADO
    c, _, df = _rodar_reservatorios(corpo)
    assert 39145550 not in set(df["codigo_estacao"]) and c.descartes["sem_data_da_leitura"] == 1
    assert isinstance(df, pd.DataFrame)
