"""Conectores Open-Meteo (dados reais de modelos meteorológicos, sem cadastro).

- histórico: reanálise ERA5 → `tipo = derivada` (não é medição de estação)
- previsão: chuva horária até 72 h → `tipo = prevista`, com horário de emissão
- maré: nível do mar previsto (inclui a maré astronômica) → `tipo = prevista`

Um ponto representativo de cada distrito sanitário (calculado das geometrias oficiais).
Termos de uso: gratuito para uso não comercial — confirmar para uso institucional.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pandas as pd
import requests

from climasense.etl import gold
from climasense.etl.conectores.base import Conector, ExecucaoCtx, FonteInfo
from climasense.territorio.carga import geo_local
from climasense.territorio.geometria import ponto_representativo

PONTO_MARE_RECIFE = (-34.86, -8.06)  # mar em frente ao Porto do Recife (lon, lat)


def pontos_distritos() -> list[tuple[str, float, float]]:
    return [
        (f"ds-{f['properties']['cdistscodi']}", *ponto_representativo(f["geometry"]))
        for f in geo_local()["features"]
    ]


class _OpenMeteo(Conector):
    url: str
    variavel_api: str
    variavel: str
    unidade: str
    parametros_extra: dict = {}

    def __init__(self, http=None, **kw) -> None:
        super().__init__(**kw)
        self.http = http or requests.Session()

    def pontos(self) -> list[tuple[str, float, float]]:
        return pontos_distritos()

    def parametros(self, ctx: ExecucaoCtx) -> dict:
        return {}

    def extrair(self, ctx: ExecucaoCtx) -> list[dict]:
        registros = []
        for territorio_id, lon, lat in self.pontos():
            params = {
                "latitude": round(lat, 4),
                "longitude": round(lon, 4),
                "hourly": self.variavel_api,
                "timezone": "GMT",
                **self.parametros_extra,
                **self.parametros(ctx),
            }
            r = self.http.get(self.url, params=params, timeout=60)
            r.raise_for_status()
            corpo = r.json()
            horas, valores = corpo["hourly"]["time"], corpo["hourly"][self.variavel_api]
            registros.extend(
                {"territorio_id": territorio_id, "hora_utc": h, "valor": v, "lat": lat, "lon": lon}
                for h, v in zip(horas, valores, strict=True)
            )
        return registros

    def transformar(self, bruto: pd.DataFrame, ctx: ExecucaoCtx) -> pd.DataFrame:
        df = pd.DataFrame(
            {
                "fonte_id": self.id,
                "territorio_id": bruto["territorio_id"],
                "variavel": self.variavel,
                "valor": pd.to_numeric(bruto["valor"], errors="coerce"),  # nulo continua nulo (RN-02)
                "unidade": self.unidade,
                "tipo": self.fonte.tipo,
                "observado_em": pd.to_datetime(bruto["hora_utc"], utc=True),
                "coletado_em": ctx.agora,
                "qualidade": "ok",
            }
        )
        df.loc[df["valor"].isna(), "qualidade"] = "ausente"
        if self.fonte.tipo == "prevista":
            df["emitido_em"] = ctx.agora
            df["horizonte_h"] = (
                ((df["observado_em"] - ctx.agora).dt.total_seconds() // 3600).clip(lower=0).astype(int)
            )
        self.descartes = {}
        return df

    def gravar_silver(self, df: pd.DataFrame, ctx: ExecucaoCtx) -> int:
        colunas = [
            "fonte_id",
            "territorio_id",
            "variavel",
            "valor",
            "unidade",
            "tipo",
            "observado_em",
            "emitido_em",
            "horizonte_h",
            "coletado_em",
            "qualidade",
        ]
        return self.load.salvar_silver(df, ctx.engine, "observacoes", "silver", ctx.execucao_id, colunas)


class ConectorOpenMeteoHistorico(_OpenMeteo):
    id = "open-meteo-historico"
    fonte = FonteInfo(
        "Chuva horária por distrito (reanálise ERA5)",
        "Open-Meteo / Copernicus ECMWF",
        "https://open-meteo.com/en/docs/historical-weather-api",
        "derivada",
        "CC BY 4.0",
    )
    url = "https://archive-api.open-meteo.com/v1/archive"
    variavel_api, variavel, unidade = "precipitation", "chuva_mm", "mm"
    inicio_padrao = date(2021, 1, 1)

    def parametros(self, ctx: ExecucaoCtx) -> dict:
        # a reanálise chega com alguns dias de atraso; pedimos até 7 dias atrás
        fim = (ctx.agora - timedelta(days=7)).date()
        dias = ctx.limite or (fim - self.inicio_padrao).days
        return {"start_date": (fim - timedelta(days=dias)).isoformat(), "end_date": fim.isoformat()}

    def gerar_gold(self, ctx: ExecucaoCtx) -> None:
        with ctx.engine.begin() as c:
            gold.chuva(c)


class ConectorOpenMeteoPrevisao(_OpenMeteo):
    id = "open-meteo-previsao"
    fonte = FonteInfo(
        "Chuva prevista por distrito (até 72 h)",
        "Open-Meteo",
        "https://open-meteo.com/en/docs",
        "prevista",
        "CC BY 4.0",
    )
    url = "https://api.open-meteo.com/v1/forecast"
    variavel_api, variavel, unidade = "precipitation", "chuva_mm", "mm"
    parametros_extra = {"forecast_days": 3}


class ConectorOpenMeteoMare(_OpenMeteo):
    id = "open-meteo-mare"
    fonte = FonteInfo(
        "Nível do mar previsto em frente ao Recife (inclui a maré)",
        "Open-Meteo Marine",
        "https://open-meteo.com/en/docs/marine-weather-api",
        "prevista",
        "CC BY 4.0",
    )
    url = "https://marine-api.open-meteo.com/v1/marine"
    variavel_api, variavel, unidade = "sea_level_height_msl", "mare_m", "m"
    parametros_extra = {"forecast_days": 3}

    def pontos(self):
        return [("recife", *PONTO_MARE_RECIFE)]


def agora_utc() -> datetime:
    return datetime.now(UTC)
