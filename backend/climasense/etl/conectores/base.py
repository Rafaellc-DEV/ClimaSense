"""Classe abstrata Conector (POO): cada fonte real é uma subclasse que combina Extract, Transform e Load.

`executar()` é o método-modelo comum: extrai → bronze (acumulativa) → transforma → silver → gold.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd
from sqlalchemy import Engine

from climasense.config import Configuracao
from climasense.etl.load import Load


@dataclass(frozen=True)
class FonteInfo:
    nome: str
    orgao: str
    url: str
    tipo: str  # observada | prevista | derivada
    licenca: str | None = None


@dataclass
class ExecucaoCtx:
    execucao_id: str
    config: Configuracao
    mongo: Any
    engine: Engine
    agora: datetime
    limite: int | None = None


@dataclass
class ResultadoExecucao:
    lidos: int = 0
    gravados: int = 0
    descartados: int = 0
    motivos: dict[str, int] = field(default_factory=dict)


class ConectorPlanejado(NotImplementedError):
    """A fonte está especificada, mas ainda não foi integrada (aparece como “Planejada”)."""


class Conector(ABC):
    id: str
    fonte: FonteInfo
    banco_bronze: str = "bronze"

    def __init__(self, load: Load | None = None) -> None:
        self.load = load or Load()

    def colecao_bronze(self, ctx: ExecucaoCtx):
        return ctx.mongo[self.banco_bronze][self.id.replace("-", "_")]

    @abstractmethod
    def extrair(self, ctx: ExecucaoCtx) -> list[dict]: ...

    @abstractmethod
    def transformar(self, bruto: pd.DataFrame, ctx: ExecucaoCtx) -> pd.DataFrame: ...

    @abstractmethod
    def gravar_silver(self, df: pd.DataFrame, ctx: ExecucaoCtx) -> int: ...

    def gerar_gold(self, ctx: ExecucaoCtx) -> None:  # opcional por fonte
        return None

    def ler_bronze(self, ctx: ExecucaoCtx) -> pd.DataFrame:
        docs = list(
            self.colecao_bronze(ctx).find(
                {"_execucao_id": ctx.execucao_id},
                {"_id": 0, "_data_carga": 0, "_execucao_id": 0, "_fonte": 0},
            )
        )
        return pd.DataFrame(docs)

    def executar(self, ctx: ExecucaoCtx) -> ResultadoExecucao:
        resultado = ResultadoExecucao()
        registros = self.extrair(ctx)
        resultado.lidos = len(registros)
        self.load.salvar_bronze(self.colecao_bronze(ctx), registros, self.id, ctx.execucao_id)
        bruto = self.ler_bronze(ctx)
        df = self.transformar(bruto, ctx) if not bruto.empty else bruto
        resultado.gravados = self.gravar_silver(df, ctx) if not df.empty else 0
        resultado.motivos = dict(getattr(self, "descartes", {}))
        resultado.descartados = sum(resultado.motivos.values())
        self.gerar_gold(ctx)
        return resultado
