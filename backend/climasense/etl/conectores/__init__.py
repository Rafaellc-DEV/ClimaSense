"""Registro de conectores: um por fonte real."""

from climasense.etl.conectores.open_meteo import (
    ConectorOpenMeteoHistorico,
    ConectorOpenMeteoMare,
    ConectorOpenMeteoPrevisao,
)
from climasense.etl.conectores.planejados import (
    ConectorAnaTelemetria,
    ConectorApacChuva,
    ConectorCemaden,
    ConectorInmet,
    ConectorMareMarinha,
    ConectorRecifeAlagamento,
)
from climasense.etl.conectores.vacinacao import ConectorVacinacao

CONECTORES = {
    c.id: c
    for c in (
        ConectorVacinacao,
        ConectorOpenMeteoHistorico,
        ConectorOpenMeteoPrevisao,
        ConectorOpenMeteoMare,
        ConectorAnaTelemetria,
        ConectorApacChuva,
        ConectorInmet,
        ConectorCemaden,
        ConectorRecifeAlagamento,
        ConectorMareMarinha,
    )
}
IMPLEMENTADOS = {"vacinacao", "open-meteo-historico", "open-meteo-previsao", "open-meteo-mare"}
