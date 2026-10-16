"""Carga no Atlas (mongomock, com os arquivos oficiais reais), hidrografia simplificada e mapa portátil."""

import json

import mongomock
import pytest

from climasense.territorio import carga, mapa_portatil


@pytest.fixture(scope="module")
def geo():
    return carga.geo_local()


@pytest.fixture(scope="module")
def faixas():
    return carga.preparar_hidrografia(carga.carregar_hidrografia())


def test_geo_local_bate_com_o_arquivo_enriquecido_da_aula_07(geo):
    referencia = json.loads((carga.DATA / "distritos-enriquecidos.geojson").read_text(encoding="utf-8"))
    for nova, antiga in zip(geo["features"], referencia["features"], strict=True):
        for chave in (
            "cdistscodi",
            "nome_distrito",
            "bairros",
            "quantidade_bairros",
            "area_km2",
            "codigos_originais_csv",
        ):
            assert nova["properties"][chave] == antiga["properties"][chave], chave


def test_upsert_nao_duplica_e_leitura_exige_os_oito(geo):
    cliente = mongomock.MongoClient()
    assert carga.salvar_atlas(cliente, geo, "Recife") == 8
    carga.salvar_atlas(cliente, geo, "Recife")
    assert cliente["Recife"]["DistritosSanitarios"].count_documents({}) == 8
    assert len(carga.ler_atlas(cliente, "Recife")["features"]) == 8
    cliente["Recife"]["DistritosSanitarios"].delete_one({"properties.cdistscodi": 3})
    with pytest.raises(carga.ErroTerritorio, match="oito distritos"):
        carga.ler_atlas(cliente, "Recife")


def test_hidrografia_81_feicoes_com_nome_e_bacia_e_versao_leve(faixas):
    assert len(faixas) == 81
    assert all("nome" in f["properties"] and "bacia" in f["properties"] for f in faixas)
    original = len(json.dumps([f["geometry"] for f in faixas]))
    leve = len(json.dumps([f["geometry_web"] for f in faixas]))
    assert leve < original * 0.5
    cliente = mongomock.MongoClient()
    carga.salvar_hidrografia(cliente, faixas, "Recife")
    carga.salvar_hidrografia(cliente, faixas, "Recife")
    web = carga.ler_hidrografia(cliente, "Recife")
    assert len(web["features"]) == 81
    assert len(json.dumps(web)) < 600_000


def test_slug_dos_bairros():
    assert carga.slug("Brasília Teimosa") == "brasilia-teimosa"
    assert carga.slug("Ilha do retiro") == "ilha-do-retiro"


def test_mapa_portatil_tem_8_distritos_81_faixas_e_a_origem(geo, faixas):
    water = {
        "type": "FeatureCollection",
        "features": [{k: v for k, v in f.items() if k != "geometry_web"} for f in faixas],
    }
    html = mapa_portatil.gerar(geo, water, "arquivos oficiais locais")
    assert html.count('"cdistscodi"') >= 8
    assert '"waterCount": 81' in html
    assert "arquivos oficiais locais" in html
    assert "AtlasModel" in html and "__MAP__" not in html
