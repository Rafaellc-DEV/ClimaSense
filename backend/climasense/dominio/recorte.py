"""Recorte de território e período (RF-05) e conversões de fuso (RN-16). Domínio puro: sem I/O."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

FUSO_RECIFE = ZoneInfo("America/Recife")
_PADRAO_TERRITORIO = re.compile(r"^(recife|ds-[1-8]|bairro-[a-z0-9]+(?:-[a-z0-9]+)*)$")


class RecorteInvalido(ValueError):
    """Território ou período inválido, com mensagem pronta para a tela."""


def validar_territorio(territorio_id: str) -> str:
    if not _PADRAO_TERRITORIO.match(territorio_id):
        raise RecorteInvalido(
            f"Território “{territorio_id}” não existe. Use “recife”, um distrito (ds-1 a ds-8) ou um bairro."
        )
    return territorio_id


def granularidade(territorio_id: str) -> str:
    if territorio_id == "recife":
        return "municipio"
    return "distrito" if territorio_id.startswith("ds-") else "bairro"


@dataclass(frozen=True)
class Recorte:
    territorio_id: str
    inicio: date
    fim: date

    def __post_init__(self) -> None:
        validar_territorio(self.territorio_id)
        if self.inicio > self.fim:
            raise RecorteInvalido("A data de início precisa ser anterior ou igual à data de fim.")

    @property
    def granularidade(self) -> str:
        return granularidade(self.territorio_id)

    def intervalo_utc(self) -> tuple[datetime, datetime]:
        """[início do 1º dia, início do dia seguinte ao último) no horário do Recife, convertido para UTC."""
        return inicio_do_dia_utc(self.inicio), inicio_do_dia_utc(self.fim + timedelta(days=1))


def inicio_do_dia_utc(dia: date) -> datetime:
    return datetime.combine(dia, time.min, tzinfo=FUSO_RECIFE).astimezone(UTC)


def para_recife(momento: datetime) -> datetime:
    if momento.tzinfo is None:
        raise ValueError("Horário sem fuso: o ClimaSense armazena tudo em UTC com fuso explícito.")
    return momento.astimezone(FUSO_RECIFE)


def dia_no_recife(momento: datetime) -> date:
    return para_recife(momento).date()
