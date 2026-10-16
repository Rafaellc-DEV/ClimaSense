"""Load — porte da classe do Projeto-ETL_AVD. Mudança exigida pela RN-09: a bronze passa a ser ACUMULATIVA
(cada carga leva _execucao_id; nada é apagado). A silver grava em silver.vacinados (a view
public.silver_vacinados mantém o nome antigo)."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
from sqlalchemy import Engine

LOTE_BRONZE = 5000

COLUNAS_SILVER_VACINADOS = [
    "faixa_etaria",
    "idade",
    "sexo",
    "raca_cor",
    "municipio",
    "grupo",
    "categoria",
    "lote",
    "vacina",
    "dose",
    "data_vacinacao",
    "distrito_sanitario",
    "unidade_saude",
    "sistema_origem",
]


class Load:
    """Grava os dados: na camada BRONZE (MongoDB Atlas) ou na SILVER (Postgres/Neon)."""

    def salvar_bronze(self, colecao, registros: list[dict], fonte_id: str, execucao_id: str) -> int:
        agora = datetime.now(UTC)
        documentos = [
            {**r, "_fonte": fonte_id, "_execucao_id": execucao_id, "_data_carga": agora} for r in registros
        ]
        for d in documentos:
            d.pop("_id", None)  # o _id do CKAN não pode colidir com o _id do Mongo
        # Em lotes: o histórico do Open-Meteo passa de 400 mil documentos, e um único insert_many
        # estoura o tempo limite de socket do Atlas.
        for i in range(0, len(documentos), LOTE_BRONZE):
            colecao.insert_many(documentos[i : i + LOTE_BRONZE], ordered=False)
        print(f"[load] {len(documentos)} documentos gravados na bronze")
        return len(documentos)

    def salvar_silver(
        self,
        df: pd.DataFrame,
        engine: Engine,
        tabela: str,
        esquema: str,
        execucao_id: str,
        colunas: list[str],
    ) -> int:
        saida = df.reindex(columns=colunas).copy()
        saida["execucao_id"] = execucao_id
        saida.to_sql(
            tabela, engine, schema=esquema, if_exists="append", index=False, method="multi", chunksize=1000
        )
        print(f"[load] {len(saida)} linhas gravadas em {esquema}.{tabela}")
        return len(saida)
