import copy

import mongomock
import pytest

from climasense.etl.conectores import CONECTORES, IMPLEMENTADOS
from climasense.etl.conectores.base import Conector, ConectorPlanejado
from climasense.etl.extract import Extract
from climasense.etl.load import Load
from tests.unit.etl.registros_ckan import REGISTROS, HttpCkan


def test_extract_pagina_de_500_respeita_o_limite_e_guarda_o_total():
    http = HttpCkan(REGISTROS * 60, total=1_400_000)  # 1.020 registros disponíveis
    e = Extract("https://api", "rid", limite=1000, http=http)
    assert len(e.ler_api()) == 1000
    assert [p["offset"] for p in http.pedidos] == [0, 500]
    assert e.total_fonte == 1_400_000


def test_bronze_e_acumulativa_e_le_so_o_lote_pedido():
    colecao = mongomock.MongoClient()["bronze"]["recife_alagamento"]
    load = Load()
    load.salvar_bronze(colecao, copy.deepcopy(REGISTROS[:3]), "recife-alagamento", "exec-1")
    load.salvar_bronze(colecao, copy.deepcopy(REGISTROS[:2]), "recife-alagamento", "exec-2")
    assert colecao.count_documents({}) == 5  # nada foi apagado (RN-09)
    lote = Extract("u", "r", 1).ler_bronze(colecao, "exec-2")
    assert len(lote) == 2 and "_execucao_id" not in lote and "_fonte" not in lote


def test_todos_os_conectores_sao_subclasses_de_conector():
    assert all(issubclass(c, Conector) for c in CONECTORES.values())
    assert set(CONECTORES) >= IMPLEMENTADOS
    assert "vacinacao" not in CONECTORES  # o produto foca desastres naturais (0009)


@pytest.mark.parametrize("fonte_id", sorted(set(CONECTORES) - IMPLEMENTADOS))
def test_conectores_planejados_avisam_em_vez_de_inventar_dados(fonte_id):
    with pytest.raises(ConectorPlanejado, match="planejado"):
        CONECTORES[fonte_id]().extrair(None)
