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
from sqlalchemy import text

from climasense.etl import gold
from climasense.etl.conectores import comum
from climasense.etl.conectores.base import Conector, ExecucaoCtx, FonteInfo, FonteSemDados
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
    minimo_horas_futuras = 0

    def __init__(self, http=None, **kw) -> None:
        super().__init__(**kw)
        self.http = http or comum.sessao_http()

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
            hourly = corpo.get("hourly", {}) if isinstance(corpo, dict) else {}
            horas, valores = hourly.get("time"), hourly.get(self.variavel_api)
            if (
                not isinstance(horas, list)
                or not isinstance(valores, list)
                or not horas
                or len(horas) != len(valores)
            ):
                raise FonteSemDados("Open-Meteo sem série horária válida para um dos territórios.")
            registros.extend(
                {"territorio_id": territorio_id, "hora_utc": h, "valor": v, "lat": lat, "lon": lon}
                for h, v in zip(horas, valores, strict=True)
            )
        return registros

    def validar(self, df: pd.DataFrame, ctx: ExecucaoCtx) -> None:
        if df.empty:
            raise FonteSemDados("Open-Meteo sem registros utilizáveis nesta coleta.")
        validos = df[df["valor"].notna()]
        if set(validos["territorio_id"]) != {t for t, _, _ in self.pontos()}:
            raise FonteSemDados("Open-Meteo sem valores utilizáveis para todos os territórios da fonte.")
        inicio = ctx.agora.replace(minute=0, second=0, microsecond=0)
        esperadas = {inicio + timedelta(hours=h) for h in range(self.minimo_horas_futuras)}
        if esperadas and any(
            not esperadas.issubset(set(grupo["observado_em"])) or grupo["observado_em"].duplicated().any()
            for _, grupo in validos.groupby("territorio_id")
        ):
            raise FonteSemDados(
                "Open-Meteo sem cobertura horária completa das próximas 72 h; carga anterior preservada."
            )

    def transformar(self, bruto: pd.DataFrame, ctx: ExecucaoCtx) -> pd.DataFrame:
        df = pd.DataFrame(
            {
                "fonte_id": self.id,
                "territorio_id": bruto["territorio_id"],
                "variavel": self.variavel,
                "valor": bruto["valor"].map(comum.numero if self.variavel == "chuva_mm" else comum.real),
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
        if self.fonte.tipo != "prevista":
            df = self._sem_repetidas(df, ctx)
        if df.empty:
            return 0
        return self.load.salvar_silver(df, ctx.engine, "observacoes", "silver", ctx.execucao_id, colunas)

    def _sem_repetidas(self, df: pd.DataFrame, ctx: ExecucaoCtx) -> pd.DataFrame:
        """Observada/derivada não muda entre cargas: só entra na silver o que ainda não está lá com o mesmo
        valor (a janela de uma atualização se sobrepõe à anterior). A bronze continua guardando tudo."""
        with ctx.engine.connect() as c:
            existentes = pd.read_sql(
                text(
                    "select territorio_id, observado_em, valor from silver.observacoes "
                    "where fonte_id = :f and observado_em between :a and :b"
                ),
                c,
                params={"f": self.id, "a": df["observado_em"].min(), "b": df["observado_em"].max()},
            )
        if existentes.empty:
            return df
        chave = ["territorio_id", "observado_em", "valor"]
        existentes["observado_em"] = pd.to_datetime(existentes["observado_em"], utc=True)
        marcado = df.merge(existentes.drop_duplicates().assign(_ja=True), on=chave, how="left")
        return df[marcado["_ja"].isna().to_numpy()]


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
    minimo_horas_futuras = 72
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
    # past_days: as horas já passadas do modelo cobrem os ~7 dias em que a ERA5 ainda não chegou (fallback da
    # chuva recente, depois da APAC observada). Cada emissão é acumulativa na silver (nada é sobrescrito).
    # Dias de calendário: três dias deixam menos de 72 h futuras após a meia-noite UTC.
    parametros_extra = {"forecast_days": 4, "past_days": 7}


class ConectorOpenMeteoMare(_OpenMeteo):
    minimo_horas_futuras = 72
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
    parametros_extra = {"forecast_days": 4}

    def pontos(self):
        return [("recife", *PONTO_MARE_RECIFE)]


def agora_utc() -> datetime:
    return datetime.now(UTC)


class ConectorOpenMeteoTemperatura(_OpenMeteo):
    """Temperatura do ar a 2 m: PREVISÃO de modelo, nunca temperatura medida (a única estação medida do Recife, a
    A301 do INMET, exige token). Vai para `silver.observacoes` (`temp_c`, `tipo = prevista`)."""

    id = "open-meteo-temperatura"
    fonte = FonteInfo(
        "Temperatura do ar prevista por modelo (2 m)",
        "Open-Meteo",
        "https://open-meteo.com/en/docs",
        "prevista",
        "CC BY 4.0",
    )
    url = "https://api.open-meteo.com/v1/forecast"
    variavel_api, variavel, unidade = "temperature_2m", "temp_c", "°C"
    parametros_extra = {"forecast_days": 3, "past_days": 1}


CAMADAS_SOLO = {"soil_moisture_0_to_7cm": "0_7cm", "soil_moisture_7_to_28cm": "7_28cm"}
SOLO_MIN_HORAS_DIA = 24  # dia do histórico só entra com as 24 h (média diária de dia incompleto não vale)


class ConectorOpenMeteoSolo(Conector):
    """Umidade do solo (m³/m³) ESTIMADA por modelo: não existe medida pública no Recife (RN-11: Experimental).

    - padrão (`previsao`): modelo ECMWF IFS pelo `api.open-meteo.com` (2 dias passados + 3 dias à frente);
      silver guarda o estado mais recente de cada hora (a bronze guarda cada resposta, por execução).
    - `historico`: ERA5-Land (`archive-api`), média diária por ponto, base do percentil do próprio ponto. A
      reanálise chega com ~5-7 dias de atraso.
    Hora sem valor não vira linha (lacuna, nunca zero). O percentil e a classe saem da gold."""

    id = "open-meteo-solo"
    fonte = FonteInfo(
        "Umidade do solo estimada por modelo (0-7 cm e 7-28 cm)",
        "Open-Meteo / ECMWF (IFS e ERA5-Land)",
        "https://open-meteo.com/en/docs",
        "derivada",
        "CC BY 4.0",
    )
    url_previsao = "https://api.open-meteo.com/v1/forecast"
    url_historico = "https://archive-api.open-meteo.com/v1/archive"
    inicio_padrao = date(2021, 1, 1)

    def __init__(self, http=None, **kw) -> None:
        super().__init__(**kw)
        self.http = http or comum.sessao_http()
        self.descartes: dict[str, int] = {}

    def colecao_bronze(self, ctx: ExecucaoCtx):
        nome = "open_meteo_solo_historico" if ctx.modo == "historico" else "open_meteo_solo"
        return ctx.mongo[self.banco_bronze][nome]

    def extrair(self, ctx: ExecucaoCtx) -> list[dict]:
        if ctx.modo not in (None, "previsao", "historico"):
            raise ValueError(f"Modo desconhecido: {ctx.modo}")
        historico = ctx.modo == "historico"
        extra: dict = {"forecast_days": 3, "past_days": 2}
        if historico:
            fim = (ctx.agora - timedelta(days=7)).date()
            dias = ctx.limite or (fim - self.inicio_padrao).days
            extra = {"start_date": (fim - timedelta(days=dias)).isoformat(), "end_date": fim.isoformat()}
        registros = []
        for territorio_id, lon, lat in pontos_distritos():
            r = self.http.get(
                self.url_historico if historico else self.url_previsao,
                params={
                    "latitude": round(lat, 4),
                    "longitude": round(lon, 4),
                    "hourly": ",".join(CAMADAS_SOLO),
                    "timezone": "GMT",
                    **extra,
                },
                timeout=90,
            )
            r.raise_for_status()
            hora = r.json()["hourly"]
            registros.append(
                {
                    "territorio_id": territorio_id,
                    "lat": lat,
                    "lon": lon,
                    "time": hora["time"],
                    **{api: hora[api] for api in CAMADAS_SOLO},
                }
            )
        return registros

    def transformar(self, bruto: pd.DataFrame, ctx: ExecucaoCtx) -> pd.DataFrame:
        self.descartes = {}
        linhas = []
        for r in bruto.to_dict("records"):
            for api, camada in CAMADAS_SOLO.items():
                for h, v in zip(r["time"], r[api], strict=True):
                    linhas.append((r["territorio_id"], camada, h, v))
        df = pd.DataFrame(linhas, columns=["territorio_id", "camada", "hora", "valor"])
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
        df["observado_em"] = pd.to_datetime(df["hora"], utc=True)
        sem_valor = df["valor"].isna()
        fora = ~sem_valor & ~df["valor"].between(0, 1)
        if sem_valor.any():
            self.descartes["hora_sem_valor"] = int(sem_valor.sum())
        if fora.any():
            self.descartes["valor_fora_da_faixa"] = int(fora.sum())
        df = df[~sem_valor & ~fora].drop(columns="hora")
        if ctx.modo != "historico" or df.empty:
            return df
        df["dia"] = df["observado_em"].dt.date
        dia = (
            df.groupby(["territorio_id", "camada", "dia"])["valor"]
            .agg(media_m3m3="mean", n_horas="count")
            .reset_index()
        )
        incompletos = dia["n_horas"] < SOLO_MIN_HORAS_DIA
        if incompletos.any():
            self.descartes["dia_incompleto"] = int(incompletos.sum())
        return dia[~incompletos]

    def gravar_silver(self, df: pd.DataFrame, ctx: ExecucaoCtx) -> int:
        extra = {"agora": ctx.agora, "ex": ctx.execucao_id}
        with ctx.engine.begin() as c:
            if ctx.modo == "historico":
                c.execute(
                    text(
                        "insert into silver.solo_modelo_diario (territorio_id, camada, dia, media_m3m3, n_horas, "
                        "coletado_em, execucao_id) values (:t, :c, :d, :m, :n, :agora, :ex) "
                        "on conflict (territorio_id, camada, dia) do update set media_m3m3 = excluded.media_m3m3, "
                        "n_horas = excluded.n_horas, coletado_em = excluded.coletado_em, "
                        "execucao_id = excluded.execucao_id"
                    ),
                    [
                        {
                            "t": r.territorio_id,
                            "c": r.camada,
                            "d": r.dia,
                            "m": float(r.media_m3m3),
                            "n": int(r.n_horas),
                        }
                        | extra
                        for r in df.itertuples()
                    ],
                )
            else:
                c.execute(
                    text(
                        "insert into silver.solo_modelo_horario (territorio_id, camada, observado_em, valor_m3m3, "
                        "emitido_em, coletado_em, execucao_id) values (:t, :c, :o, :v, :agora, :agora, :ex) "
                        "on conflict (territorio_id, camada, observado_em) do update set "
                        "valor_m3m3 = excluded.valor_m3m3, emitido_em = excluded.emitido_em, "
                        "coletado_em = excluded.coletado_em, execucao_id = excluded.execucao_id"
                    ),
                    [
                        {
                            "t": r.territorio_id,
                            "c": r.camada,
                            "o": r.observado_em.to_pydatetime(),
                            "v": float(r.valor),
                        }
                        | extra
                        for r in df.itertuples()
                    ],
                )
        return len(df)

    def gerar_gold(self, ctx: ExecucaoCtx) -> None:
        with ctx.engine.begin() as c:
            gold.recalcular(c, gold.TABELAS_SOLO)
