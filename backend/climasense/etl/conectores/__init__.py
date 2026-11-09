"""Registro de conectores: um por fonte real."""

from climasense.etl.conectores.alagamento import ConectorRecifeAlagamento
from climasense.etl.conectores.alagamento_2026 import ConectorRecifeAlagamento2026
from climasense.etl.conectores.alertas import ConectorAlertasOficiais
from climasense.etl.conectores.apac import ConectorApacChuva
from climasense.etl.conectores.apac_previsao import ConectorApacPrevisao
from climasense.etl.conectores.apac_reservatorios import ConectorApacReservatorios
from climasense.etl.conectores.apac_rios import ConectorApacRios
from climasense.etl.conectores.arboviroses import ConectorRecifeArboviroses
from climasense.etl.conectores.areas_risco import ConectorRecifeAreasRisco
from climasense.etl.conectores.atendimentos_grau import ConectorRecifeAtendimentosGrauRisco
from climasense.etl.conectores.atlas import ConectorAtlasDesastres
from climasense.etl.conectores.cnes import ConectorCnesEquipamentos
from climasense.etl.conectores.ibge_censo import ConectorIbgeCenso2022Bairro
from climasense.etl.conectores.infodengue import ConectorInfoDengue
from climasense.etl.conectores.leptospirose import ConectorSinanLeptospirose
from climasense.etl.conectores.open_meteo import (
    ConectorOpenMeteoHistorico,
    ConectorOpenMeteoMare,
    ConectorOpenMeteoPrevisao,
    ConectorOpenMeteoSolo,
    ConectorOpenMeteoTemperatura,
)
from climasense.etl.conectores.planejados import (
    ConectorAnaTelemetria,
    ConectorCemaden,
    ConectorInmet,
    ConectorMareMarinha,
)
from climasense.etl.conectores.samu import ConectorSamuRecife
from climasense.etl.conectores.sisagua import ConectorSisagua
from climasense.etl.conectores.suscetibilidade import ConectorSgbSuscetibilidadeDeslizamento

CONECTORES = {
    c.id: c
    for c in (
        ConectorOpenMeteoHistorico,
        ConectorOpenMeteoPrevisao,
        ConectorOpenMeteoMare,
        ConectorApacChuva,
        ConectorApacPrevisao,
        ConectorOpenMeteoSolo,
        ConectorOpenMeteoTemperatura,
        ConectorApacRios,
        ConectorApacReservatorios,
        ConectorAlertasOficiais,
        ConectorRecifeAlagamento,
        ConectorCnesEquipamentos,
        ConectorIbgeCenso2022Bairro,
        ConectorRecifeAreasRisco,
        ConectorSgbSuscetibilidadeDeslizamento,
        ConectorRecifeAtendimentosGrauRisco,
        ConectorRecifeAlagamento2026,
        ConectorInfoDengue,
        ConectorSinanLeptospirose,
        ConectorRecifeArboviroses,
        ConectorSamuRecife,
        ConectorSisagua,
        ConectorAtlasDesastres,
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
    "apac-previsao",
    "open-meteo-solo",
    "open-meteo-temperatura",
    "apac-rios",
    "apac-reservatorios",
    "alertas-oficiais",
    "recife-alagamento",
    "infodengue",
    "sinan-leptospirose",
    "recife-arboviroses",
    "samu-recife",
    "sisagua",
    "atlas-desastres",
    "cnes-equipamentos",
    "ibge-censo-2022-bairro",
    "recife-areas-risco",
    "sgb-suscetibilidade-deslizamento",
    "recife-atendimentos-grau-risco",
    "recife-alagamento-2026",
}
# Modos aceitos por `etl run <fonte> --modo`
MODOS = {
    "apac-chuva": ("tempo-real", "historico"),
    "open-meteo-solo": ("previsao", "historico"),
    "apac-rios": ("24h", "72h"),
}
