"""Transform — porte da classe do Projeto-ETL_AVD (mesmos métodos), contando os descartes por motivo."""

from __future__ import annotations

import pandas as pd

COLUNAS_TEXTO = [
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


class Transform:
    """Limpa e padroniza os dados da BRONZE para a SILVER."""

    def __init__(self) -> None:
        self.descartes: dict[str, int] = {}

    def limpar_textos(self, df: pd.DataFrame) -> pd.DataFrame:
        for coluna in COLUNAS_TEXTO:
            if coluna not in df:
                df[coluna] = None
            df[coluna] = df[coluna].astype("string").str.strip().str.upper()
            df[coluna] = df[coluna].replace("", None)  # texto vazio vira nulo
        return df

    def converter_tipos(self, df: pd.DataFrame) -> pd.DataFrame:
        df["idade"] = pd.to_numeric(df.get("idade"), errors="coerce")
        df["dose"] = pd.to_numeric(df.get("descricao_dose"), errors="coerce")
        df["data_vacinacao"] = pd.to_datetime(df.get("data_vacinacao"), errors="coerce").dt.date
        return df

    def criar_colunas(self, df: pd.DataFrame) -> pd.DataFrame:
        # "3 - COMIRNATY (PFIZER)" -> "COMIRNATY (PFIZER)"
        df["vacina"] = df["vacina_fabricante"].str.split(" - ", n=1).str[1]
        # "DS 4: CNES: 0000639 - UBS JOAQUIM CAVALCANTE" -> "DS 4" e "UBS JOAQUIM CAVALCANTE"
        df["distrito_sanitario"] = df["cnes"].str.split(":").str[0]
        df["unidade_saude"] = df["cnes"].str.split(" - ", n=1).str[1]
        return df.drop(columns=["vacina_fabricante", "cnes", "descricao_dose"], errors="ignore")

    def remover_invalidos(self, df: pd.DataFrame) -> pd.DataFrame:
        antes = len(df)
        df = df.dropna(subset=["idade", "data_vacinacao"])
        self.descartes["idade_ou_data_invalida"] = antes - len(df)
        antes = len(df)
        df = df.drop_duplicates()
        self.descartes["duplicado"] = antes - len(df)
        return df

    def limpar(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self.limpar_textos(df)
        df = self.converter_tipos(df)
        df = self.criar_colunas(df)
        df = self.remover_invalidos(df)
        print(f"[transform] {len(df)} linhas prontas para a silver")
        return df
