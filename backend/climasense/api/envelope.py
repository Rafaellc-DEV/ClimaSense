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
    limite_frescor_h: float | None = Field(
        default=None, description="Idade máxima aceita do dado, em horas; null = fonte sem limite definido"
    )
    desatualizado: bool | None = Field(
        default=None,
        description="true = passou do limite; false = em dia; null = sem dado ou sem limite (nunca 'em dia' por "
        "falta de dado, RN-01)",
    )


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
    fonte_por_premissa: dict[str, str] | None = Field(
        default=None, description="Simulador: id estável da fonte de cada premissa (chuva_prevista_mm etc.)"
    )
    dados_insuficientes: bool = False
    supressao_minima: int | None = Field(
        default=None,
        description="Contagens por território abaixo deste valor (e maiores que zero) saem nulas e com "
        "suprimido=true (RNF-03, RN-13)",
    )


class RespostaDados(BaseModel, Generic[T]):
    dados: T
    meta: Meta
