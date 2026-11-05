"""Registro de conectores: um por fonte real."""

from climasense.etl.conectores.abrigos import ConectorRecifeAbrigos
from climasense.etl.conectores.alagamento import ConectorRecifeAlagamento
from climasense.etl.conectores.alertas import ConectorAlertasOficiais
from climasense.etl.conectores.apac import ConectorApacChuva
from climasense.etl.conectores.arboviroses import ConectorRecifeArboviroses
from climasense.etl.conectores.infodengue import ConectorInfoDengue
from climasense.etl.conectores.leptospirose import ConectorSinanLeptospirose
from climasense.etl.conectores.open_meteo import (
    ConectorOpenMeteoHistorico,
    ConectorOpenMeteoMare,
    ConectorOpenMeteoPrevisao,
)
from climasense.etl.conectores.planejados import (
    ConectorAnaTelemetria,
    ConectorCemaden,
    ConectorInmet,
    ConectorMareMarinha,
)

CONECTORES = {
    c.id: c
    for c in (
        ConectorOpenMeteoHistorico,
        ConectorOpenMeteoPrevisao,
        ConectorOpenMeteoMare,
        ConectorApacChuva,
        ConectorAlertasOficiais,
        ConectorRecifeAlagamento,
        ConectorRecifeAbrigos,
        ConectorInfoDengue,
        ConectorSinanLeptospirose,
        ConectorRecifeArboviroses,
        ConectorAnaTelemetria,
        ConectorInmet,
        ConectorCemaden,
        ConectorMareMarinha,
    )
}
IMPLEMENTADOS = {
    "open-meteo-historico",
    "open-meteo-previsao",
    "open-meteo-mare",
    "apac-chuva",
    "alertas-oficiais",
    "recife-alagamento",
    "recife-abrigos",
    "infodengue",
    "sinan-leptospirose",
    "recife-arboviroses",
}
# Modos aceitos por `etl run <fonte> --modo`
MODOS = {"apac-chuva": ("tempo-real", "historico"), "recife-abrigos": ("cadastro", "ativos")}
