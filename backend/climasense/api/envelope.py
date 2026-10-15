"""Envelope das respostas analíticas (T2.7, design §6.1).

Todo valor exibido se relaciona a uma fonte e a um horário (CA-02); a falta de dados é explícita (RN-01).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

TipoFonte = Literal["observada", "prevista", "derivada"]
StatusFonte = Literal["atualizada", "desatualizada", "com_falha", "planejada"]


class FonteMeta(BaseModel):
    id: str
    nome: str
    tipo: TipoFonte
    atualizado_em: datetime | None = None
    status: StatusFonte


class RecorteMeta(BaseModel):
    territorio_id: str
    inicio: date | None = None
    fim: date | None = None
    granularidade: Literal["municipio", "distrito", "bairro"]


class Amostra(BaseModel):
    """Indicador calculado sobre extração parcial (RN-10)."""

    n: int = Field(ge=0)
    total_fonte: int | None = Field(default=None, ge=0)


class Meta(BaseModel):
    fontes: list[FonteMeta] = Field(min_length=1)
    recorte: RecorteMeta | None = None
    cobertura_pct: float | None = Field(default=None, ge=0, le=100)
    amostra: Amostra | None = None
    avisos: list[str] = []
    dados_insuficientes: bool = False


class RespostaDados(BaseModel, Generic[T]):
    dados: T
    meta: Meta
