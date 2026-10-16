import copy

import mongomock
import pandas as pd
import pytest

from climasense.etl.conectores import CONECTORES, IMPLEMENTADOS
from climasense.etl.conectores.base import Conector, ConectorPlanejado
from climasense.etl.extract import Extract
from climasense.etl.load import Load
from climasense.etl.transform import Transform
from tests.unit.etl.registros_ckan import REGISTROS, HttpCkan


class TransformOriginal:
    """Cópia literal da classe do Projeto-ETL_AVD/src/transformer.py, usada como referência."""

    def limpar_textos(self, df):
        colunas_texto = [
            "faixa_etaria",
            "sexo",
            "raca_cor",
            "municipio",
            "grupo",
            "categoria",
            "lote",
            "vacina_fabricante",
            "cnes",
            "sistema_origem",
        ]
        for coluna in colunas_texto:
            df[coluna] = df[coluna].str.strip().str.upper()
            df[coluna] = df[coluna].replace("", None)
        return df

    def converter_tipos(self, df):
        df["idade"] = pd.to_numeric(df["idade"], errors="coerce")
        df["dose"] = pd.to_numeric(df["descricao_dose"], errors="coerce")
        df["data_vacinacao"] = pd.to_datetime(df["data_vacinacao"], errors="coerce").dt.date
        return df

    def criar_colunas(self, df):
        df["vacina"] = df["vacina_fabricante"].str.split(" - ", n=1).str[1]
        df["distrito_sanitario"] = df["cnes"].str.split(":").str[0]
        df["unidade_saude"] = df["cnes"].str.split(" - ", n=1).str[1]
        return df.drop(columns=["vacina_fabricante", "cnes", "descricao_dose"])

    def remover_invalidos(self, df):
        df = df.dropna(subset=["idade", "data_vacinacao"])
        return df.drop_duplicates()

    def limpar(self, df):
        return self.remover_invalidos(self.criar_colunas(self.converter_tipos(self.limpar_textos(df))))


def _df():
    return pd.DataFrame([{k: v for k, v in r.items() if k != "_id"} for r in copy.deepcopy(REGISTROS)])


def test_transform_da_o_mesmo_resultado_do_etl_original():
    novo = Transform().limpar(_df())
    original = TransformOriginal().limpar(_df())
    pd.testing.assert_frame_equal(
        novo.reset_index(drop=True).astype(object),
        original.reset_index(drop=True).astype(object),
        check_dtype=False,
    )
    linha = novo.iloc[0]
    assert (linha["vacina"], linha["distrito_sanitario"], linha["unidade_saude"]) == (
        "COMIRNATY (PFIZER)",
        "DS 4",
        "UBS JOAQUIM CAVALCANTE",
    )
    assert linha["sexo"] == "FEMININO" and linha["faixa_etaria"] == "60 A 69 ANOS"


def test_transform_conta_os_descartes_por_motivo():
    t = Transform()
    assert len(t.limpar(_df())) == 1
    assert t.descartes == {"idade_ou_data_invalida": 2, "duplicado": 1}


def test_extract_pagina_de_500_respeita_o_limite_e_guarda_o_total():
    http = HttpCkan(REGISTROS * 300, total=1_400_000)  # 1.200 registros disponíveis
    e = Extract("https://api", "rid", limite=1000, http=http)
    assert len(e.ler_api()) == 1000
    assert [p["offset"] for p in http.pedidos] == [0, 500]
    assert e.total_fonte == 1_400_000


def test_bronze_e_acumulativa_e_le_so_o_lote_pedido():
    colecao = mongomock.MongoClient()["vacinacao"]["bronze_vacinados"]
    load = Load()
    load.salvar_bronze(colecao, copy.deepcopy(REGISTROS), "vacinacao", "exec-1")
    load.salvar_bronze(colecao, copy.deepcopy(REGISTROS[:2]), "vacinacao", "exec-2")
    assert colecao.count_documents({}) == 6  # nada foi apagado (RN-09)
    lote = Extract("u", "r", 1).ler_bronze(colecao, "exec-2")
    assert len(lote) == 2 and "_execucao_id" not in lote and "_fonte" not in lote


def test_todos_os_conectores_sao_subclasses_de_conector():
    assert all(issubclass(c, Conector) for c in CONECTORES.values())
    assert set(CONECTORES) >= IMPLEMENTADOS


@pytest.mark.parametrize("fonte_id", sorted(set(CONECTORES) - IMPLEMENTADOS))
def test_conectores_planejados_avisam_em_vez_de_inventar_dados(fonte_id):
    with pytest.raises(ConectorPlanejado, match="planejado"):
        CONECTORES[fonte_id]().extrair(None)
