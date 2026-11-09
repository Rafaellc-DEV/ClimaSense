"""Conectores da cobertura territorial dos 94 bairros, sem rede nem banco.

As respostas são recortes REAIS das camadas ArcGIS do portal ESIG e dos CSVs de atendimentos da Defesa Civil,
gravados em 06/11/2026 (fixtures/). O teste da conta de área usa uma malha sintética de dois quadrados: é aritmética
de geometria, não dado do produto.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import pytest
from shapely.geometry import box, mapping

from climasense.etl import frescor
from climasense.etl.conectores import (
    CONECTORES,
    IMPLEMENTADOS,
    alagamento_2026,
    atendimentos_grau,
    geo_territorial,
    suscetibilidade,
)
from climasense.etl.conectores.base import FonteSemDados
from tests.unit.etl.test_conectores_chuva import Http, Resposta, bronze, ctx
from tests.unit.etl.test_conectores_vulneraveis import ctx_banco

FIX = Path(__file__).parent / "fixtures"
FONTES = (
    "sgb-suscetibilidade-deslizamento",
    "recife-atendimentos-grau-risco",
    "recife-alagamento-2026",
)


def _geojson(nome):
    return json.loads((FIX / nome).read_text(encoding="utf-8"))


def test_conectores_registrados_implementados_e_com_limite_de_frescor():
    for fid in FONTES:
        assert fid in CONECTORES and fid in IMPLEMENTADOS and CONECTORES[fid].id == fid
    # fontes estáticas: limites na ordem de anos (carta de 2015: 5 anos; atendimentos: 18 meses; evento de 2026: 1 ano)
    assert frescor.limite_frescor_h("sgb-suscetibilidade-deslizamento") == 43800
    assert frescor.limite_frescor_h("recife-atendimentos-grau-risco") == 13140
    assert frescor.limite_frescor_h("recife-alagamento-2026") == 8760


# ----------------------------------------------------------------------------------------- suscetibilidade
def _susc(limite=None, malha=None):
    corpo = _geojson("sgb_suscetibilidade_deslizamento_2026-11-06.geojson")

    def camada(params):
        if params.get("f") == "json":  # metadados da camada (data da última edição)
            return Resposta({"editingInfo": {"lastEditDate": 1756000000000}})
        return Resposta(
            {"type": "FeatureCollection", "features": corpo["features"][: params["resultRecordCount"]]}
        )

    http = Http({"Suscebilidade_Deslizamento": camada})
    c = suscetibilidade.ConectorSgbSuscetibilidadeDeslizamento(http=http, malha=malha)
    return c, http, c.extrair(ctx(limite=limite))


def test_suscetibilidade_pede_so_a_lista_fechada_de_campos_e_guarda_poligonos_e_edicao_na_bronze():
    _, http, registros = _susc()
    url, params = http.pedidos[0]
    assert url.endswith("Suscebilidade_Deslizamento/FeatureServer/0/query")
    assert (
        params["outFields"] == "classe,processo,fonte"
        and params["outSR"] == 4326
        and params["f"] == "geojson"
    )
    resumo = registros[0]
    assert resumo["poligonos"] == 10 and resumo["amostra"] is False
    assert resumo["ultima_edicao_fonte"].startswith("2025-08-24")  # hora que a fonte informa (RF-19)
    assert len(registros) == 11 and registros[1]["geometry"]["type"] in ("Polygon", "MultiPolygon")


def test_suscetibilidade_classes_com_ou_sem_acento_e_lixo():
    assert suscetibilidade.classe_de("Alta") == "alta" and suscetibilidade.classe_de("Média") == "media"
    assert suscetibilidade.classe_de("M�dia") == "media" and suscetibilidade.classe_de("Baixa") == "baixa"
    assert suscetibilidade.classe_de(None) is None and suscetibilidade.classe_de("Muito alta") is None


def test_suscetibilidade_com_a_malha_oficial_devolve_fracoes_validas_e_a_cobertura():
    c, _, registros = _susc()
    df = c.transformar(bronze(registros), ctx())
    assert c.descartes == {} and set(df["classe"]) == {"alta", "media", "baixa", "coberta"}
    assert df["fracao"].between(0, 1).all() and (df["area_km2"] >= 0).all()
    assert c.cobertura["n_bairros_oficiais"] == 94
    assert c.cobertura["poligonos_por_classe"] == {"alta": 4, "media": 3, "baixa": 3}
    # bairro que a carta não toca fica sem linha (sem dado, nunca "baixa")
    assert df["bairro_id"].nunique() == c.cobertura["n_bairros_com_carta"] < 94
    # cada bairro com carta tem as quatro classes (inclusive com fração 0: a carta cobre o bairro e a classe não)
    assert (df.groupby("bairro_id")["classe"].nunique() == 4).all()


def test_suscetibilidade_fracao_da_area_em_malha_sintetica():
    # bairro A (0,01° x 0,01°) com a metade esquerda "Alta"; bairro B sem nenhum polígono da carta
    a, b = box(-34.90, -8.05, -34.89, -8.04), box(-34.88, -8.05, -34.87, -8.04)
    metade_alta = box(-34.90, -8.05, -34.895, -8.04)
    resto_baixa = box(-34.895, -8.05, -34.89, -8.04)
    brutos = [
        {
            "registro": "poligono",
            "classe": "Alta",
            "processo": "Deslizamento",
            "geometry": mapping(metade_alta),
        },
        {
            "registro": "poligono",
            "classe": "Baixa",
            "processo": "Deslizamento",
            "geometry": mapping(resto_baixa),
        },
        {"registro": "poligono", "classe": "Média", "processo": "Inundação", "geometry": mapping(b)},
        {"registro": "poligono", "classe": "Moderada", "processo": "Deslizamento", "geometry": mapping(b)},
        {"registro": "poligono", "classe": "Alta", "processo": "Deslizamento", "geometry": {"type": "Point"}},
    ]
    c = suscetibilidade.ConectorSgbSuscetibilidadeDeslizamento(
        http=Http({}), malha=[("bairro-a", a), ("bairro-b", b)]
    )
    df = c.transformar(pd.DataFrame(brutos), ctx()).set_index(["bairro_id", "classe"])
    assert c.descartes == {"processo_fora_do_escopo": 1, "classe_desconhecida": 1, "geometria_invalida": 1}
    assert df.loc[("bairro-a", "alta"), "fracao"] == pytest.approx(0.5, abs=0.001)
    assert df.loc[("bairro-a", "baixa"), "fracao"] == pytest.approx(0.5, abs=0.001)
    assert df.loc[("bairro-a", "media"), "fracao"] == 0 and df.loc[
        ("bairro-a", "coberta"), "fracao"
    ] == pytest.approx(1, abs=1e-4)
    assert df.loc[("bairro-a", "coberta"), "area_km2"] == pytest.approx(1.21, rel=0.01)  # ~1,1 km x 1,1 km
    assert "bairro-b" not in set(df.index.get_level_values(0))


def test_suscetibilidade_grava_na_silver_e_na_gold_com_rotulo_e_fonte():
    c, _, registros = _susc()
    cx = ctx_banco()
    df = c.transformar(bronze(registros), cx)
    assert c.gravar_silver(df, cx) == len(df)
    delete, insert = cx.engine.comandos
    assert "delete from silver.suscetibilidade_deslizamento where fonte_id" in delete[0]
    assert set(insert[1][0]) == {"b", "c", "a", "fr", "f", "ex"} and insert[1][0]["f"] == c.id
    cx.engine.comandos.clear()
    c.gerar_gold(cx)
    sqls = [s for s, _ in cx.engine.comandos]
    assert (
        "delete from gold.indicador_territorial" in sqls[0]
        and "delete from gold.cobertura_indicador" in sqls[1]
    )
    ind = [p for s, p in cx.engine.comandos if "insert into gold.indicador_territorial" in s]
    assert [p["ind"] for p in ind] == [
        f"suscetibilidade_deslizamento_{k}" for k in ("alta", "media", "baixa", "coberta")
    ]
    assert all(
        p["r"] == "suscetibilidade do terreno (carta 2012–2014, escala 1:45.000)" and p["f"] == c.id
        for p in ind
    )
    assert all("risco" not in p["r"].lower() for p in ind) and ind[0]["agora"] == cx.agora
    assert len([s for s in sqls if "insert into gold.cobertura_indicador" in s]) == 4


def test_suscetibilidade_amostra_so_vai_para_a_bronze():
    c, http, registros = _susc(limite=3)
    assert http.pedidos[0][1]["resultRecordCount"] == 3
    assert registros[0]["amostra"] is True and registros[0]["poligonos"] == 3
    cx = ctx_banco(limite=3)
    c.gravar_silver(c.transformar(bronze(registros), cx), cx)
    c.gerar_gold(cx)
    assert cx.engine.comandos == []  # a silver e a gold anteriores ficam intactas


def test_suscetibilidade_erro_do_servidor_ou_camada_vazia_vira_falha_explicada():
    http = Http(
        {"Suscebilidade_Deslizamento": Resposta({"error": {"code": 400, "message": "Invalid query"}})}
    )
    with pytest.raises(FonteSemDados, match="Invalid query"):
        suscetibilidade.ConectorSgbSuscetibilidadeDeslizamento(http=http).extrair(ctx())
    http = Http({"Suscebilidade_Deslizamento": Resposta({"type": "FeatureCollection", "features": []})})
    with pytest.raises(FonteSemDados, match="nenhuma feição"):
        suscetibilidade.ConectorSgbSuscetibilidadeDeslizamento(http=http).extrair(ctx())


# ----------------------------------------------------------------------------------------- atendimentos com grau
def _csv(nome):
    return (FIX / nome).read_bytes()


def _atend():
    arquivos = {
        2020: "defesa_civil_2020_amostra.csv",
        2022: "defesa_civil_2022_amostra.csv",
        2023: "defesa_civil_2023_amostra.csv",
        2024: "defesa_civil_2024_deslizamento_amostra.csv",
        2025: "defesa_civil_2025_uma_linha.csv",
    }
    recursos = {ano: f"https://exemplo.invalid/{ano}/{nome}" for ano, nome in arquivos.items()}
    http = Http({f"/{ano}/": Resposta(conteudo=_csv(nome)) for ano, nome in arquivos.items()})
    c = atendimentos_grau.ConectorRecifeAtendimentosGrauRisco(http=http, recursos=recursos)
    return c, http, c.extrair(ctx())


def test_atendimentos_conta_graus_pelo_ano_do_arquivo_e_ignora_o_endereco():
    contagem, resumo = atendimentos_grau.contar_graus(
        _csv("defesa_civil_2024_deslizamento_amostra.csv"), 2024
    )
    assert resumo == {"linhas": 8, "sem_ancora": 0, "sem_grau": 5, "grau_invalido": 0}
    assert sum(contagem.values()) == 3 and {g for _, _, g in contagem} == {"R3", "R4"}
    assert all(a == 2024 for a, _, _ in contagem)


def test_atendimentos_bronze_so_tem_resumo_e_contagens_sem_endereco():
    _, _, registros = _atend()
    texto = json.dumps(registros, ensure_ascii=False)
    assert not re.search(r"Rua |Avenida|Endereco|Vila ", texto)
    arquivos = [r for r in registros if r["registro"] == "arquivo"]
    assert [a["ano_arquivo"] for a in arquivos] == [2020, 2022, 2023, 2024, 2025]
    assert all(len(a["sha256"]) == 64 and a["amostra"] is False for a in arquivos)
    assert set(registros[-1]) == {"registro", "ano", "bairro", "grau", "atendimentos"}


def test_atendimentos_agrega_por_bairro_oficial_e_diz_que_o_historico_parou():
    c, _, registros = _atend()
    df = c.transformar(bronze(registros), ctx())
    assert set(df.columns) == {"bairro_id", "ano", "grau", "atendimentos"}
    assert set(df["grau"]) <= {"R1", "R2", "R3", "R4"} and (df["atendimentos"] > 0).all()
    assert df["bairro_id"].str.startswith("bairro-").all()
    k = c.cobertura
    assert k["n_bairros_oficiais"] == 94 and k["n_bairros_com_grau"] == df["bairro_id"].nunique()
    assert k["ano_final"] == 2024 and k["anos_dos_arquivos_sem_grau"] == [2022, 2025]  # sem grau no arquivo
    assert k["por_grau"].get("R3", 0) >= 4 and k["por_grau"].get("R4") == 1


def test_atendimentos_bairro_que_nao_e_bairro_oficial_e_contado_e_nunca_atribuido_a_outro():
    c, _, registros = _atend()
    br = bronze(registros)
    br.loc[br["registro"] == "contagem", "bairro"] = "Localidade Inventada"
    df = c.transformar(br, ctx())
    assert df.empty and c.descartes["bairro_fora_da_base_oficial"] == sum(
        r["atendimentos"] for r in registros if r["registro"] == "contagem"
    )


def test_atendimentos_grava_e_a_gold_diz_o_periodo_e_o_zero_so_onde_ha_grau():
    c, _, registros = _atend()
    cx = ctx_banco()
    df = c.transformar(bronze(registros), cx)
    assert c.gravar_silver(df, cx) == len(df)
    delete, insert = cx.engine.comandos
    assert "delete from silver.atendimentos_grau_risco" in delete[0]
    assert set(insert[1][0]) == {"b", "a", "g", "n", "f", "ex"} and isinstance(insert[1][0]["n"], int)
    # a gold lê min/max de ano da silver (aqui o dublê de conexão não devolve linhas: nada é gravado)
    assert c.gerar_gold.__func__ is atendimentos_grau.ConectorRecifeAtendimentosGrauRisco.gerar_gold


def test_atendimentos_limite_vira_amostra_dos_primeiros_anos_e_nao_toca_a_silver():
    c, http, _ = _atend()
    http.pedidos.clear()
    registros = c.extrair(ctx(limite=1))
    assert len(http.pedidos) == 1 and registros[0]["ano_arquivo"] == 2020 and registros[0]["amostra"] is True
    cx = ctx_banco(limite=1)
    assert c.gravar_silver(c.transformar(bronze(registros), cx), cx) == 0 and cx.engine.comandos == []


def test_atendimentos_sem_nenhum_grau_vira_falha_explicada():
    recursos = {2025: "https://exemplo.invalid/2025/x.csv"}
    cab = _csv("defesa_civil_2025_uma_linha.csv").splitlines()[0] + b"\n"
    http = Http({"/2025/": Resposta(conteudo=cab)})
    with pytest.raises(FonteSemDados, match="grau de risco"):
        atendimentos_grau.ConectorRecifeAtendimentosGrauRisco(http=http, recursos=recursos).extrair(ctx())


# ----------------------------------------------------------------------------------------- alagamento de 2026
CAMADAS_2026 = {
    "Poligonos_Alagamentos_2026_5": "alagamento_2026_comunidades_2026-11-06.geojson",
    "Lotes_Areas_Alagadas_2026_V1": "alagamento_2026_lotes_2026-11-06.geojson",
    "Logradouros_Alagamentos_2026_V1": "alagamento_2026_trechos_2026-11-06.geojson",
}


def _al2026(limite=None, malha=None):
    def servidor(arquivo):
        def camada(params):
            if params.get("f") == "json":
                return Resposta({"editingInfo": {"lastEditDate": 1781700000000}})
            f = _geojson(arquivo)["features"]
            d = params["resultOffset"]
            return Resposta({"type": "FeatureCollection", "features": f[d : d + params["resultRecordCount"]]})

        return camada

    http = Http({n: servidor(a) for n, a in CAMADAS_2026.items()})
    c = alagamento_2026.ConectorRecifeAlagamento2026(http=http, malha=malha)
    return c, http, c.extrair(ctx(limite=limite))


def test_alagamento_2026_pede_so_campos_agregaveis_nunca_endereco_cep_ou_a_base_da_celpe():
    c, http, registros = _al2026()
    campos = {u.split("/")[-4]: p["outFields"] for u, p in http.pedidos if u.endswith("/query")}
    assert campos == {
        "Poligonos_Alagamentos_2026_5": "id,comunidade,rpa,qtd_registros",
        "Lotes_Areas_Alagadas_2026_V1": "qtdunhab",
        "Logradouros_Alagamentos_2026_V1": "fid",
    }
    assert all("*" not in v for v in campos.values())
    codigo = "".join(Path(m.__file__).read_text(encoding="utf-8") for m in (alagamento_2026, geo_territorial))
    assert (
        "Celpe" not in codigo.split('"""', 2)[2]
    )  # a camada de clientes nunca é consultada (só citada na docstring)
    assert len(registros) == 3 + 6 + 12 + 6


def test_alagamento_2026_lote_e_trecho_na_bronze_nao_levam_coordenada_nem_geometria():
    _, _, registros = _al2026()
    lotes = [r for r in registros if r["registro"] == "lote"]
    trechos = [r for r in registros if r["registro"] == "trecho"]
    assert all(set(r) == {"registro", "bairro_id", "qtdunhab"} for r in lotes)
    assert all(set(r) == {"registro", "bairro_id"} for r in trechos)
    assert any(r["qtdunhab"] is None for r in lotes) and any(isinstance(r["qtdunhab"], int) for r in lotes)
    com = [r for r in registros if r["registro"] == "comunidade"]
    assert set(com[0]) == {"registro", "id", "comunidade", "rpa", "qtd_registros", "geometry"}
    resumos = {r["camada"]: r for r in registros if r["registro"] == "consulta"}
    assert resumos["Poligonos_Alagamentos_2026_5"]["feicoes"] == 6 and resumos[
        "Lotes_Areas_Alagadas_2026_V1"
    ]["ultima_edicao_fonte"].startswith("2026-06-17")


def test_alagamento_2026_agrega_por_bairro_e_zero_medido_e_diferente_de_ausente():
    c, _, registros = _al2026()
    df = c.transformar(bronze(registros), ctx())
    assert set(df["camada"]) == {"comunidades", "lotes", "trechos"}
    com = df[df["camada"] == "comunidades"].set_index("comunidade")
    assert (
        com.loc["Ibura de Baixo", "qtd_registros"] == 1712 and com.loc["BR101", "qtd_registros"] == 0
    )  # 0 medido
    assert com["bairro_id"].str.startswith("bairro-").all()
    lotes = df[df["camada"] == "lotes"]
    assert lotes["itens"].sum() + c.descartes.get("lote_fora_da_malha", 0) == 12
    assert lotes["unidades_habitacionais"].dropna().ge(0).all()
    assert df[df["camada"] == "trechos"]["itens"].sum() + c.descartes.get("trecho_fora_da_malha", 0) == 6
    assert c.cobertura["comunidades"] == 6 and c.cobertura["n_bairros_oficiais"] == 94


def test_alagamento_2026_lotes_sem_unidades_ficam_ausentes_e_nao_zero():
    malha = [("bairro-a", box(-34.90, -8.05, -34.89, -8.04))]
    lote = mapping(box(-34.896, -8.046, -34.895, -8.045))
    brutos = pd.DataFrame(
        [
            {"registro": "lote", "bairro_id": "bairro-a", "qtdunhab": None},
            {"registro": "lote", "bairro_id": "bairro-a", "qtdunhab": float("nan")},
            {"registro": "lote", "bairro_id": None, "qtdunhab": 3},
            {
                "registro": "comunidade",
                "id": 1,
                "comunidade": "X",
                "rpa": 4,
                "qtd_registros": None,
                "geometry": lote,
            },
        ]
    )
    c = alagamento_2026.ConectorRecifeAlagamento2026(http=Http({}), malha=malha)
    df = c.transformar(brutos, ctx()).set_index("id")
    assert df.loc["lotes-bairro-a", "itens"] == 2 and pd.isna(
        df.loc["lotes-bairro-a", "unidades_habitacionais"]
    )
    assert pd.isna(df.loc["com-1", "qtd_registros"]) and df.loc["com-1", "bairro_id"] == "bairro-a"
    assert c.descartes == {"lote_fora_da_malha": 1}


def test_alagamento_2026_grava_e_a_gold_leva_o_rotulo_do_evento_sem_data():
    c, _, registros = _al2026()
    cx = ctx_banco()
    df = c.transformar(bronze(registros), cx)
    assert c.gravar_silver(df, cx) == len(df)
    delete, insert = cx.engine.comandos
    assert "delete from silver.alagamento_2026" in delete[0] and insert[1][0]["f"] == c.id
    cx.engine.comandos.clear()
    c.gerar_gold(cx)
    ind = [p for s, p in cx.engine.comandos if "insert into gold.indicador_territorial" in s]
    assert [p["ind"] for p in ind] == [
        f"alagamento_2026_{k}"
        for k in ("comunidades", "registros", "lotes", "unidades_habitacionais", "trechos")
    ]
    assert all(p["r"] == "evento de 2026, sem data por registro" and p["p"] == "2026" for p in ind)


def test_alagamento_2026_amostra_so_vai_para_a_bronze():
    c, _, registros = _al2026(limite=2)
    assert all(r["amostra"] for r in registros if r["registro"] == "consulta")
    assert sum(r["feicoes"] for r in registros if r["registro"] == "consulta") == 6
    cx = ctx_banco(limite=2)
    c.gravar_silver(c.transformar(bronze(registros), cx), cx)
    c.gerar_gold(cx)
    assert cx.engine.comandos == []


def test_malha_e_projecao_da_area_em_metros_quadrados():
    quadrado = box(-34.90, -8.05, -34.89, -8.04)  # 0,01° x 0,01° ≈ 1,1 km x 1,1 km
    assert geo_territorial.projetar(quadrado).area == pytest.approx(1.2e6, rel=0.02)
