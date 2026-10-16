"""Conector da vacinação COVID-19 — o ETL do Projeto-ETL_AVD, agora como subclasse de Conector."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from climasense.etl import gold
from climasense.etl.conectores.base import Conector, ExecucaoCtx, FonteInfo
from climasense.etl.extract import Extract
from climasense.etl.load import COLUNAS_SILVER_VACINADOS
from climasense.etl.transform import Transform

# Fonte: https://dados.recife.pe.gov.br/dataset/perfil-das-pessoas-vacinadas-covid-19
URL_API = "https://dados.recife.pe.gov.br/api/3/action/datastore_search"
RESOURCE_ID = "164e7f11-2855-421b-89ea-64ea485ae09d"


class ConectorVacinacao(Conector):
    id = "vacinacao"
    fonte = FonteInfo(
        "Perfil das pessoas vacinadas — COVID-19",
        "Prefeitura do Recife (Dados Abertos)",
        "https://dados.recife.pe.gov.br/dataset/perfil-das-pessoas-vacinadas-covid-19",
        "observada",
        "ODbL",
    )
    banco_bronze = "vacinacao"

    def __init__(self, extract: Extract | None = None, transform: Transform | None = None, **kw) -> None:
        super().__init__(**kw)
        self.extract = extract
        self.transform = transform or Transform()
        self.total_fonte: int | None = None

    def colecao_bronze(self, ctx: ExecucaoCtx):
        return ctx.mongo[ctx.config.mongo_db_bronze_vacinacao][
            "bronze_vacinados"
        ]  # mesmo nome do ETL anterior

    def extrair(self, ctx: ExecucaoCtx) -> list[dict]:
        self.extract = self.extract or Extract(
            URL_API, RESOURCE_ID, ctx.limite or ctx.config.etl_limite_vacinacao
        )
        registros = self.extract.ler_api()
        self.total_fonte = self.extract.total_fonte
        return registros

    def transformar(self, bruto: pd.DataFrame, ctx: ExecucaoCtx) -> pd.DataFrame:
        df = self.transform.limpar(bruto)
        self.descartes = self.transform.descartes
        return df

    def gravar_silver(self, df: pd.DataFrame, ctx: ExecucaoCtx) -> int:
        return self.load.salvar_silver(
            df, ctx.engine, "vacinados", "silver", ctx.execucao_id, COLUNAS_SILVER_VACINADOS
        )

    def gerar_gold(self, ctx: ExecucaoCtx) -> None:
        with ctx.engine.begin() as c:
            gold.vacinacao(c, ctx.execucao_id, self.total_fonte, ctx.config.supressao_minima)


def ultima_execucao_com_silver(engine) -> str | None:
    with engine.connect() as c:
        return c.execute(text("select execucao_id from silver.vacinados order by id desc limit 1")).scalar()
