"""Conectores do foco em chuvas com respostas REAIS gravadas em 04/11/2026 (fixtures/), sem rede nem banco.

Onde um caso positivo não existia no dia da gravação (nenhum alerta para o Recife), o teste altera um campo da
resposta real e diz qual; nenhuma resposta inteira é inventada.
"""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from climasense.etl.conectores import abrigos, alagamento, alertas, apac, comum
from climasense.etl.conectores.base import ExecucaoCtx, FonteSemDados

FIX = Path(__file__).parent / "fixtures"
AGORA = datetime(2026, 11, 5, 2, 0, tzinfo=UTC)  # 23:00 de 04/11 no Recife


def _json(nome):
    return json.loads((FIX / nome).read_text(encoding="utf-8"))


class Resposta:
    def __init__(self, corpo=None, conteudo: bytes | None = None, erro=None):
        self.corpo, self.erro = corpo, erro
        self.content = conteudo if conteudo is not None else json.dumps(corpo).encode()

    def json(self):
        return self.corpo if self.corpo is not None else json.loads(self.content)

    def raise_for_status(self):
        if self.erro:
            raise self.erro


class Http:
    """Dublê: casa a URL pedida com um trecho e devolve a resposta gravada."""

    def __init__(self, rotas: dict):
        self.rotas, self.pedidos = rotas, []

    def get(self, url, params=None, timeout=None):
        self.pedidos.append((url, params))
        for trecho, resposta in self.rotas.items():
            if trecho in url:
                return resposta(params) if callable(resposta) else resposta
        raise AssertionError(f"URL inesperada: {url}")


def ctx(modo=None, agora=AGORA, limite=None):
    return ExecucaoCtx("exec-1", None, None, None, agora, limite, modo)


def bronze(registros):
    """O que volta do Mongo: os mesmos documentos, sem as colunas técnicas."""
    return pd.DataFrame(copy.deepcopy(registros))


# ----------------------------------------------------------------------------------------- APAC
def test_apac_tempo_real_associa_estacao_ao_bairro_e_traco_vira_ausente():
    corpo = _json("apac_precipitacao_acumulada_2026-11-04.json")
    c = apac.ConectorApacChuva(http=Http({"precipitacao_acumulada": Resposta(corpo)}))
    df = c.transformar(bronze(c.extrair(ctx())), ctx())
    assert len(c.estacoes) == 19 and len(df) == 19 * len(apac.JANELAS)
    assert c.estacoes["apac-261160617A"]["territorio_id"] == "bairro-pina"  # [CEMADEN] Pina
    assert c.estacoes["apac-261160615A"]["territorio_id"] == "bairro-cohab"  # Ibura, na malha "COHAB"
    imbiribeira = df[(df["estacao_id"] == "apac-261160609A") & (df["janela_h"] == 1)].iloc[0]
    assert pd.isna(imbiribeira["valor_mm"])  # "1_hora": "-" → ausente, não 0 (RN-02)
    assert imbiribeira["lida_em"] == datetime(2026, 11, 4, 13, 50, tzinfo=UTC)  # 10:50 no Recife (UTC−3)
    campina = df[(df["estacao_id"] == "apac-261160614A") & (df["janela_h"] == 24)].iloc[0]
    assert campina["valor_mm"] == 0.2


def test_apac_erro_com_http_200_vira_falha_explicada():
    c = apac.ConectorApacChuva(
        http=Http({"precipitacao_acumulada": Resposta({"erro": "Município inválido"})})
    )
    with pytest.raises(FonteSemDados, match="Município inválido"):
        c.extrair(ctx())


def test_apac_historico_mes_a_mes_desde_2022_e_janela_movel():
    pedidos = []

    def responde(params):
        pedidos.append(params["dataInicial"])
        return Resposta(_json("apac_historico_2026-10.json"))

    c = apac.ConectorApacChuva(http=Http({"historico_pluviometrico_mensal": responde}))
    c.extrair(ctx("historico", limite=2))
    assert pedidos == ["2026-10-01", "2026-11-01"]
    pedidos.clear()
    registros = c.extrair(ctx("historico"))
    assert pedidos[0] == "2022-01-01" and len(pedidos) == 59
    df = c.transformar(bronze(registros[:8]), ctx("historico"))
    assert {"ok"} == set(df["qualidade"]) and df["dia"].min().isoformat() == "2026-10-01"


def test_apac_historico_marca_mes_de_falha_e_pico_isolado_sem_apagar_o_bruto():
    real = _json("apac_historico_2026-10.json")[:5]
    for i, est in enumerate(real):  # outubro real foi seco: somamos 40 mm/dia para criar um mês chuvoso
        dias = est["dados"][0]["chuva_diaria"]
        for d in dias:
            dias[d] = 0 if i == 0 else round(dias[d] + 40, 2)  # a 1ª estação "travou" em zero o mês todo
    real[1]["dados"][0]["chuva_diaria"]["2026-10-15"] = 2000  # pico isolado (sensor)
    c = apac.ConectorApacChuva()
    df = c.transformar(bronze(real), ctx("historico"))
    travada = df[df["estacao_id"] == f"apac-{real[0]['codigo_gmmc']}"]
    assert set(travada["qualidade"]) == {"falha"} and travada["valor_mm"].isna().all()
    assert (travada["valor_bruto_mm"] == 0).all()  # o valor original fica guardado
    pico = df[
        (df["estacao_id"] == f"apac-{real[1]['codigo_gmmc']}") & (df["dia"].astype(str) == "2026-10-15")
    ]
    assert pico.iloc[0]["qualidade"] == "suspeito" and pd.isna(pico.iloc[0]["valor_mm"])
    assert c.descartes == {"dias_em_mes_com_falha_de_estacao": 31, "pico_isolado_suspeito": 1}


# ----------------------------------------------------------------------------------------- alertas
def _http_alertas(apac_c=None, inmet=None, cemaden=None, idap=None, quebrar=()):
    corpos = {
        "api.apac": apac_c if apac_c is not None else _json("apac_alertas_2026-11-04.json"),
        "apiprevmet3": inmet if inmet is not None else _json("inmet_avisos_ativos_2026-11-04.json"),
        "cemaden": cemaden if cemaden is not None else _json("cemaden_wsalertas2_2026-11-04.json"),
    }
    rotas = {k: Resposta(v) for k, v in corpos.items()}
    rotas["idapfile"] = Resposta(
        conteudo=idap if idap is not None else (FIX / "idap_cap_2026-11-04.xml").read_bytes()
    )
    for k in quebrar:
        import requests

        rotas[k] = Resposta({}, erro=requests.ConnectionError("fora do ar"))
    return Http(rotas)


def test_alertas_aceitam_so_o_recife_e_descartam_vencidos():
    c = alertas.ConectorAlertasOficiais(http=_http_alertas())
    agosto = datetime(2026, 8, 27, 15, 0, tzinfo=UTC)
    df = c.transformar(bronze(c.extrair(ctx(agora=agosto))), ctx(agora=agosto))
    # APAC: só os da "Metropolitana de Recife" (26 e 28/2026); em 27/08 o 26 já venceu
    assert df["codigo_fonte"].tolist() == ["28/2026"]
    linha = df.iloc[0]
    assert (linha["origem"], linha["nivel"], linha["criterio_geo"]) == ("apac", "laranja", "regiao")
    assert c.descartes["vencido:apac"] == 1 and c.descartes["fora_do_recife:apac"] == 12
    assert c.descartes["fora_do_recife:inmet"] == 3  # avisos de PE sem o Recife (geocode nem polígono)
    assert c.descartes["fora_do_recife:idap"] == 1  # baixa umidade no Sertão (polígono longe do Recife)


def test_alertas_inmet_idap_e_cemaden_com_geocode_do_recife():
    inmet = _json("inmet_avisos_ativos_2026-11-04.json")
    aviso = next(
        a for a in inmet["hoje"] + inmet["futuro"] if "26" in a["geocodes"][:2] or ",26" in a["geocodes"]
    )
    aviso["geocodes"] += ",2611606"  # ALTERADO: inclui o Recife no aviso real de PE
    aviso["fim"] = "2026-11-06 23:59"
    cap = (FIX / "idap_cap_2026-11-04.xml").read_bytes().replace(b">2600104<", b">2611606<")
    cemaden = _json("cemaden_wsalertas2_2026-11-04.json")
    cemaden["alertas"].append(
        {**cemaden["alertas"][0], "codibge": 2611606, "uf": "PE", "municipio": "RECIFE"}
    )
    c = alertas.ConectorAlertasOficiais(http=_http_alertas(inmet=inmet, cemaden=cemaden, idap=cap))
    df = c.transformar(bronze(c.extrair(ctx())), ctx())
    por = {o: g.iloc[0] for o, g in df.groupby("origem")}
    assert set(por) == {"inmet", "idap", "cemaden"}  # os da APAC já venceram em 04/11
    assert por["inmet"]["criterio_geo"] == "geocode" and por["inmet"]["nivel"] in (
        "amarelo",
        "laranja",
        "vermelho",
    )
    assert por["idap"]["codigo_fonte"] == "196332/2026" and por["idap"]["nivel"] == "laranja"  # Severe
    assert por["cemaden"]["expira_em"] is None or pd.isna(por["cemaden"]["expira_em"])


def test_alertas_poligono_que_intercepta_o_recife_conta_como_recife():
    from shapely.geometry import box

    c = alertas.ConectorAlertasOficiais(contorno=box(-35.0, -8.2, -34.8, -7.9))
    assert c._intercepta(box(-34.95, -8.1, -34.9, -8.0))
    assert not c._intercepta(box(-40.0, -9.0, -39.0, -8.5))


def test_uma_origem_fora_do_ar_nao_derruba_as_outras():
    c = alertas.ConectorAlertasOficiais(http=_http_alertas(quebrar=("idapfile", "cemaden")))
    registros = c.extrair(ctx())
    assert c.descartes == {"origem_indisponivel:cemaden": 1, "origem_indisponivel:idap": 1}
    assert any(r["origem"] == "apac" and r["tipo"] == "aviso" for r in registros)
    with pytest.raises(FonteSemDados):
        alertas.ConectorAlertasOficiais(
            http=_http_alertas(quebrar=("idapfile", "cemaden", "api.apac", "apiprevmet3"))
        ).extrair(ctx())


def test_xml_com_dtd_e_recusado():
    with pytest.raises(ValueError, match="DTD"):
        alertas.xml_seguro(b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><x>&a;</x>')


# ----------------------------------------------------------------------------------------- alagamento
def test_alagamento_le_so_categorias_e_nunca_o_endereco():
    anos = {2020: None, 2021: None, 2022: None, 2023: None}
    rotas = {
        f"/{ano}.csv": Resposta(conteudo=(FIX / f"defesa_civil_{ano}_amostra.csv").read_bytes())
        for ano in anos
    }
    c = alagamento.ConectorRecifeAlagamento(
        http=Http(rotas), recursos={ano: f"https://dados/{ano}.csv" for ano in anos}
    )
    registros = c.extrair(ctx())
    arquivos = [r for r in registros if r["tipo"] == "arquivo"]
    assert len(arquivos) == 4 and all(len(a["sha256"]) == 64 for a in arquivos)
    df = c.transformar(bronze(registros), ctx())
    # "Rua Alagoinha" (2021, vistoria de imóvel) não conta: o endereço nunca é lido; "Alagamentos" (2021) conta
    assert "2021:2" not in set(df["codigo_fonte"]) and "2021:3" in set(df["codigo_fonte"])
    assert c.descartes == {"nao_e_alagamento_nem_deslizamento": 2} and len(df) == 18
    assert set(df["tipo"]) == {"alagamento"}
    assert "bairro-dois-unidos" in set(df["territorio_id"])
    assert "bairro-areias" in set(df["territorio_id"])  # 2022 com colunas deslocadas, lido pelas âncoras
    areias = df[df["territorio_id"] == "bairro-areias"].iloc[0]
    assert areias["registrado_em"] == datetime(2022, 4, 5, tzinfo=comum.FUSO_RECIFE)
    assert df["codigo_fonte"].is_unique


def test_deslizamento_vem_da_categoria_ocorrencia_e_lona_preventiva_nao_conta():
    """Linhas reais de 2024 (endereço trocado por "(endereço omitido)")."""
    conteudo = (FIX / "defesa_civil_2024_deslizamento_amostra.csv").read_bytes()
    c = alagamento.ConectorRecifeAlagamento(
        http=Http({"/2024.csv": Resposta(conteudo=conteudo)}), recursos={2024: "https://dados/2024.csv"}
    )
    df = c.transformar(bronze(c.extrair(ctx())), ctx())
    por_tipo = df.groupby("tipo")["territorio_id"].apply(sorted).to_dict()
    assert por_tipo["deslizamento"] == [
        "bairro-agua-fria",
        "bairro-beberibe",
        "bairro-cohab",
        "bairro-dois-unidos",
    ]  # "Deslizamentos de Barreiras" e desabamento de obra de contenção (codificação mista)
    assert por_tipo["alagamento"] == ["bairro-encruzilhada", "bairro-imbiribeira"]
    # "Colocação de Lonas Plásticas" é prevenção em encosta: nem chega à bronze, e muito menos à silver
    assert len(df) == 6 and "bairro-nova-descoberta" not in set(df["territorio_id"])


# ----------------------------------------------------------------------------------------- abrigos
CURADO = (
    "nome;endereco;bairro;latitude;longitude;tipo;responsavel;fonte_url;fonte_data;observacao\n"
    "ESCOLA MUNICIPAL PROFESSOR ADAUTO PONTES;R. Sertânia, 35;Jordão;-8.135405;-34.944796;abrigo_temporario;"
    "Prefeitura do Recife;https://services7.arcgis.com/x;2025-06-13;capacidade estimada (pessoas): 100 em salas + "
    "150 em quadra, também no CKAN 2022\n"
    "ESCOLA MUNICIPAL ALTO DO PASCOAL;R. Ladeira de Pedra, 958;Agua Fria;-8.014701;-34.902125;abrigo_temporario;"
    "Prefeitura do Recife;https://services7.arcgis.com/x;2025-06-13;capacidade estimada (pessoas): 250 em salas\n"
)  # duas linhas reais de data/abrigos/abrigos-curados.csv (04/11/2026)


def _http_abrigos(cop=None):
    return Http(
        {
            "resource_show": Resposta({"result": {"last_modified": "2026-03-02T13:44:29"}}),
            "datastore_search": Resposta(_json("ckan_abrigos_datastore_2026-11-04.json")),
            "Abrigos_Ativos": Resposta(
                cop if cop is not None else _json("cop_abrigos_ativos_vazio_2026-11-04.json")
            ),
        }
    )


def test_abrigos_ckan_e_curado_sem_duplicar_o_mesmo_local(tmp_path):
    arquivo = tmp_path / "abrigos-curados.csv"
    arquivo.write_text(CURADO, encoding="utf-8")
    c = abrigos.ConectorRecifeAbrigos(http=_http_abrigos(), arquivo_curado=arquivo)
    registros = c.extrair(ctx())
    meta = next(r for r in registros if r["registro"] == "arquivo_curado")
    assert meta["linhas"] == 2 and len(meta["sha256"]) == 64
    assert not any(
        "responsavel" in r for r in registros
    )  # campo de pessoa/órgão responsável não vai à bronze
    df = c.transformar(bronze(registros), ctx())
    assert len(df) == 17 + 1 and c.descartes == {"mesmo_local_de_outra_fonte": 1}
    adauto = df[df["codigo_fonte"] == "ckan:escola-municipal-adauto-pontes"].iloc[0]
    assert adauto["capacidade_fonte"] == 250 and adauto["bairro_id"] == "bairro-jordao"
    cohab = df[df["nome"].str.contains("Sampaio Lucena")].iloc[0]
    assert cohab["bairro_id"] == "bairro-cohab"  # ponto-em-polígono, não o texto "COHAB/IBURA"


def test_feed_do_cop_nao_grava_dados_pessoais_e_feed_vazio_ainda_e_leitura():
    feicao = {
        "attributes": {
            "objectid": 1,
            "globalid": "{ABC}",
            "no_entidade": "ESCOLA MUNICIPAL ALTO DO PASCOAL",
            "latitude": -8.014701,
            "longitude": -34.902125,
            "status": "ATIVO",
            "qt_salas_utilizadas": 5,
            "qtd_pessoas_estimadas_sala": 20,
            "qtd_vagas_estimadas_quadra": 50,
            "coordenador_local": "Fulana",
            "contato_coordenador_local": "(81) 9 0000-0000",
            "last_edited_user": "servidor.x",
        }
    }  # formato da camada (campos de /FeatureServer/0?f=json); valores fictícios só para os campos pessoais
    c = abrigos.ConectorRecifeAbrigos(http=_http_abrigos({"features": [feicao]}))
    registros = c.extrair(ctx("ativos"))
    assert not any(
        k for r in registros for k in r if "coordenador" in k or "contato" in k or k.endswith("_user")
    )
    df = c.transformar(bronze(registros), ctx("ativos"))
    assert df.iloc[0]["capacidade_fonte"] == 150 and df.iloc[0]["bairro_id"] == "bairro-agua-fria"
    vazio = abrigos.ConectorRecifeAbrigos(http=_http_abrigos())
    df = vazio.transformar(bronze(vazio.extrair(ctx("ativos"))), ctx("ativos"))
    assert len(df) == 1 and df.iloc[0]["_vazio"]  # ninguém aberto agora: a carga roda e fecha os do COP


def test_capacidade_do_texto_e_mesmo_local():
    assert (
        abrigos.capacidade_do_texto("capacidade estimada (pessoas): 100 em salas + 150 em quadra, x") == 250
    )
    assert abrigos.capacidade_do_texto("sem capacidade") is None
    a = {"nome": "ESCOLA MUNICIPAL RICARDO GAMA", "latitude": -8.007459, "longitude": -34.904255}
    vizinha = {"nome": "ESCOLA MUNICIPAL PAULO VI", "latitude": -8.007, "longitude": -34.9047}
    mesma = {
        "nome": "ESCOLA MUNICIPAL PROFESSOR RICARDO GAMA",
        "latitude": -8.007374,
        "longitude": -34.904463,
    }
    assert abrigos.ConectorRecifeAbrigos._mesmo_local(a, mesma)
    assert not abrigos.ConectorRecifeAbrigos._mesmo_local(
        a, vizinha
    )  # escolas vizinhas são locais diferentes


def test_numeros_e_horas_da_fonte():
    assert comum.numero("-") is None and comum.numero(None) is None and comum.numero(-1) is None
    assert comum.numero("0") == 0.0 and comum.numero("1,5") == 1.5
    assert comum.hora_local("2026-11-04 22:30:00") == datetime(2026, 11, 5, 1, 30, tzinfo=UTC)
    assert comum.hora_local("2026-11-04T10:58:21-03:00") == datetime(2026, 11, 4, 13, 58, 21, tzinfo=UTC)


def test_endereco_de_abrigo_perde_o_brazil_do_geocodificador():
    from climasense.etl.conectores.abrigos import _endereco

    assert _endereco("R. Ramiz Galvão 218, Arruda, Recife - PE, 52120-020, Brazil") == (
        "R. Ramiz Galvão 218, Arruda, Recife - PE, 52120-020"
    )
    assert _endereco("Travessa do Gusmão, 178 - São José") == "Travessa do Gusmão, 178 - São José"
    assert _endereco("Rua X, 1, Brasil") == "Rua X, 1"
    assert _endereco(None) is None and _endereco("   ") is None
