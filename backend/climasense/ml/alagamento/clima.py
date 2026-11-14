"""Atributos de tempo: chuva ERA5 por distrito e maré astronômica em frente ao Recife.

Chuva: a mesma reanálise ERA5 e os mesmos pontos do conector `open-meteo-historico`. Primeiro lê a silver
(somente leitura); os anos que o banco não tem vêm da API de arquivo da Open-Meteo, guardados em
`tmp/alagamento/era5/` (fora do Git). A chuva é do DISTRITO: o bairro herda a do seu distrito (RN-07).

Maré: o histórico do Open-Meteo Marine só começa no fim de 2022. Como a maré astronômica é periódica, o
estudo ajusta por mínimos quadrados as principais componentes harmônicas (M2, S2, N2, K1, O1...) na série
real de 2023 em diante e reconstrói a maré de qualquer dia (antes e depois). É um cálculo determinístico da
maré astronômica, não um dado inventado; não inclui a sobre-elevação por vento e pressão.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from sqlalchemy import Engine, text

from climasense.ml.alagamento.ocorrencias import PASTA_CACHE

FONTE_HISTORICO = "open-meteo-historico"
URL_ARQUIVO = "https://archive-api.open-meteo.com/v1/archive"
URL_MARINHA = "https://marine-api.open-meteo.com/v1/marine"
FUSO_RECIFE = timedelta(hours=-3)  # sem horário de verão em Pernambuco no período estudado
PONTO_MARE = (-34.86, -8.06)  # o mesmo do conector open-meteo-mare (lon, lat)
INICIO_MARE_REAL = date(2023, 1, 1)

# Velocidades angulares (graus por hora) das componentes harmônicas usuais.
COMPONENTES = {
    "M2": 28.9841042,
    "S2": 30.0,
    "N2": 28.4397295,
    "K2": 30.0821373,
    "K1": 15.0410686,
    "O1": 13.9430356,
    "P1": 14.9589314,
    "Q1": 13.3986609,
    "M4": 57.9682084,
    "MS4": 58.9841042,
    "MN4": 57.4238337,
    "Mf": 1.0980331,
    "Mm": 0.5443747,
    "Ssa": 0.0821373,
    "Sa": 0.0410686,
}
_EPOCA = datetime(2000, 1, 1)


def pontos_distritos() -> list[tuple[str, float, float]]:
    from climasense.etl.conectores.open_meteo import pontos_distritos as pontos

    return pontos()


# ----------------------------------------------------------------------------- chuva
def _chuva_banco(engine: Engine, inicio: date, fim: date) -> pd.DataFrame:
    """Hora local (sem fuso) e mm por distrito, da silver. Somente leitura."""
    with engine.connect() as c:
        c.execute(text("SET TRANSACTION READ ONLY"))
        df = pd.read_sql(
            text(
                "select territorio_id, observado_em, valor from silver.observacoes "
                "where fonte_id = :f and observado_em >= :a and observado_em < :b"
            ),
            c,
            params={
                "f": FONTE_HISTORICO,
                "a": datetime.combine(inicio, datetime.min.time()) - FUSO_RECIFE,
                "b": datetime.combine(fim + timedelta(days=1), datetime.min.time()) - FUSO_RECIFE,
            },
        )
    if df.empty:
        return pd.DataFrame(columns=["territorio_id", "hora", "mm"])
    hora = pd.to_datetime(df["observado_em"], utc=True).dt.tz_localize(None) + FUSO_RECIFE
    out = pd.DataFrame({"territorio_id": df["territorio_id"], "hora": hora, "mm": df["valor"]})
    return out.drop_duplicates(["territorio_id", "hora"], keep="last")


def _chuva_api_ano(
    territorio_id: str, lon: float, lat: float, ano: int, fim: date, pasta: Path, http
) -> pd.DataFrame:
    destino = pasta / "era5" / f"{territorio_id}-{ano}.csv"
    if destino.exists():
        return pd.read_csv(destino, parse_dates=["hora"])
    params = {
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "hourly": "precipitation",
        "timezone": "America/Recife",
        "start_date": date(ano, 1, 1).isoformat(),
        "end_date": min(date(ano, 12, 31), fim).isoformat(),
    }
    r = http.get(URL_ARQUIVO, params=params, timeout=120)
    r.raise_for_status()
    corpo = r.json()["hourly"]
    df = pd.DataFrame(
        {"territorio_id": territorio_id, "hora": pd.to_datetime(corpo["time"]), "mm": corpo["precipitation"]}
    )
    if date(ano, 12, 31) <= fim:  # só guarda ano completo
        destino.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(destino, index=False)
    return df


def chuva_horaria(
    inicio: date, fim: date, engine: Engine | None = None, http=None, pasta: Path | None = None
) -> pd.DataFrame:
    """Chuva horária (mm) por distrito em hora local: banco primeiro, API de arquivo para o que faltar."""
    pasta = pasta or PASTA_CACHE
    vazio = pd.DataFrame({"territorio_id": [], "hora": pd.to_datetime([]), "mm": []})
    banco = _chuva_banco(engine, inicio, fim) if engine is not None else vazio
    http = http or requests.Session()
    partes = [banco]
    for territorio_id, lon, lat in pontos_distritos():
        ja = banco.loc[(banco["territorio_id"] == territorio_id) & banco["mm"].notna(), "hora"]
        anos_completos = {a for a, n in ja.dt.year.value_counts().items() if n >= 24 * 365}
        for ano in range(inicio.year, fim.year + 1):
            if ano not in anos_completos:
                partes.append(_chuva_api_ano(territorio_id, lon, lat, ano, fim, pasta, http))
    df = pd.concat([p for p in partes if not p.empty], ignore_index=True)
    df["mm"] = pd.to_numeric(df["mm"], errors="coerce")
    df = df.dropna(subset=["mm"]).drop_duplicates(["territorio_id", "hora"], keep="first")  # banco vence
    return df[(df["hora"] >= pd.Timestamp(inicio)) & (df["hora"] < pd.Timestamp(fim + timedelta(days=1)))]


def chuva_diaria(horaria: pd.DataFrame) -> pd.DataFrame:
    """Soma diária por distrito, só para dias com as 24 horas (dia incompleto fica de fora, RN-01)."""
    if horaria.empty:
        return pd.DataFrame(columns=["territorio_id", "data", "mm"])
    horaria = horaria[horaria["hora"] == horaria["hora"].dt.floor("h")]
    horaria = horaria.drop_duplicates(["territorio_id", "hora"])
    mm = pd.to_numeric(horaria["mm"], errors="coerce")
    horaria = horaria.assign(mm=mm.where(np.isfinite(mm) & (mm >= 0)))
    h = horaria.assign(data=horaria["hora"].dt.normalize())
    g = h.groupby(["territorio_id", "data"])["mm"].agg(["sum", "count"]).reset_index()
    return g[g["count"] == 24].rename(columns={"sum": "mm"})[["territorio_id", "data", "mm"]]


# ----------------------------------------------------------------------------- maré astronômica
def _matriz(horas: pd.DatetimeIndex | pd.Series) -> np.ndarray:
    t = (pd.DatetimeIndex(horas) - pd.Timestamp(_EPOCA)).total_seconds().to_numpy() / 3600.0
    colunas = [np.ones_like(t)]
    for vel in COMPONENTES.values():
        w = np.deg2rad(vel) * t
        colunas += [np.cos(w), np.sin(w)]
    return np.column_stack(colunas)


def ajustar_mare(serie: pd.DataFrame) -> dict:
    """Ajuste harmônico (mínimos quadrados) de uma série horária {hora, nivel_m}. Devolve coeficientes e erro."""
    s = serie.dropna(subset=["nivel_m"])
    A = _matriz(s["hora"])
    coef, *_ = np.linalg.lstsq(A, s["nivel_m"].to_numpy(), rcond=None)
    residuo = s["nivel_m"].to_numpy() - A @ coef
    return {
        "componentes": list(COMPONENTES),
        "coeficientes": coef.tolist(),
        "rmse_m": float(np.sqrt(np.mean(residuo**2))),
        "r2": float(1 - residuo.var() / s["nivel_m"].var()),
        "periodo": [str(s["hora"].min()), str(s["hora"].max())],
        "n_horas": int(len(s)),
    }


def prever_mare(harmonicos: dict, horas: pd.DatetimeIndex | pd.Series) -> np.ndarray:
    return _matriz(horas) @ np.asarray(harmonicos["coeficientes"])


def mare_max_diaria(harmonicos: dict, datas: pd.DatetimeIndex | pd.Series) -> pd.Series:
    """Maior nível previsto (m, relativo ao nível médio) de cada dia local, de hora em hora."""
    dias = pd.DatetimeIndex(pd.Series(datas).drop_duplicates().sort_values())
    passos = pd.to_timedelta(np.tile(np.arange(24), len(dias)), unit="h")
    horas = pd.DatetimeIndex(np.repeat(dias.values, 24)) + passos
    nivel = prever_mare(harmonicos, horas).reshape(len(dias), 24).max(axis=1)
    return pd.Series(nivel, index=dias, name="mare_max_m")


def serie_mare_real(fim: date, http=None, pasta: Path | None = None) -> pd.DataFrame:
    """Nível do mar horário do Open-Meteo Marine (hora local), de 2023 até `fim`, em cache por ano."""
    pasta = (pasta or PASTA_CACHE) / "mare"
    http = http or requests.Session()
    partes = []
    for ano in range(INICIO_MARE_REAL.year, fim.year + 1):
        destino = pasta / f"recife-{ano}.csv"
        if destino.exists():
            partes.append(pd.read_csv(destino, parse_dates=["hora"]))
            continue
        lon, lat = PONTO_MARE
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "sea_level_height_msl",
            "timezone": "America/Recife",
            "start_date": date(ano, 1, 1).isoformat(),
            "end_date": min(date(ano, 12, 31), fim).isoformat(),
        }
        r = http.get(URL_MARINHA, params=params, timeout=120)
        r.raise_for_status()
        corpo = r.json()["hourly"]
        df = pd.DataFrame({"hora": pd.to_datetime(corpo["time"]), "nivel_m": corpo["sea_level_height_msl"]})
        if date(ano, 12, 31) <= fim:
            pasta.mkdir(parents=True, exist_ok=True)
            df.to_csv(destino, index=False)
        partes.append(df)
    df = pd.concat(partes, ignore_index=True)
    df["nivel_m"] = pd.to_numeric(df["nivel_m"], errors="coerce")
    return df.dropna()
