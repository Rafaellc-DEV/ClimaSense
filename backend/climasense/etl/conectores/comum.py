"""Apoio comum aos conectores das fontes do foco em chuvas (APAC, alertas, Defesa Civil)."""

from __future__ import annotations

import functools
import math
from datetime import UTC, datetime, timedelta, timezone

import pandas as pd
import requests
from sqlalchemy import text

# O Recife não tem horário de verão desde 2019: UTC−3 fixo (evita depender do tzdata no Windows).
FUSO_RECIFE = timezone(timedelta(hours=-3), "America/Recife")
AGENTE = "ClimaSense-ETL/1.0 (Vigilancia em Saude do Recife)"
GEOCODE_RECIFE = "2611606"


def sessao_http() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = AGENTE  # algumas APIs públicas reiniciam a conexão sem User-Agent
    return s


def real(valor) -> float | None:
    """Número finito (aceita texto com vírgula); '-', '', None e texto não numérico viram None."""
    if valor is None or isinstance(valor, bool):
        return None
    try:
        v = float(str(valor).strip().replace(",", ".")) if isinstance(valor, str) else float(valor)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def numero(valor) -> float | None:
    """Medida não negativa (chuva em mm): ausente e negativos (código de erro do sensor) viram None (RN-02)."""
    v = real(valor)
    return v if v is not None and v >= 0 else None


def valor_sql(v, inteiro: bool = False):
    """Valor de um DataFrame pronto para o driver: NaN/NaT → None, numpy → Python, Timestamp → date
    e, nas colunas inteiras, 36.0 → 36 (o pandas promove inteiro com ausente a float)."""
    if v is None:
        return None
    if isinstance(v, float) and not math.isfinite(v):
        return None
    if v is pd.NaT:
        return None
    if isinstance(v, pd.Timestamp):
        return v.date()
    if hasattr(v, "item") and not isinstance(v, (str, bytes)):
        v = v.item()
        if isinstance(v, float) and not math.isfinite(v):
            return None
    if inteiro and isinstance(v, float):
        return int(round(v))
    return v


def hora_local(texto: str | None) -> datetime | None:
    """'2026-11-04 22:30:00' (hora do Recife) → datetime UTC. Texto com fuso explícito é respeitado."""
    if not texto or not str(texto).strip():
        return None
    try:
        d = datetime.fromisoformat(str(texto).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=FUSO_RECIFE)
    return d.astimezone(UTC)


@functools.lru_cache(maxsize=1)
def localizador():
    """Localizador de bairro/distrito com a base oficial local (malha de bairros + distritos sanitários)."""
    from climasense.territorio.carga import geo_local
    from climasense.territorio.geometria import Localizador, carregar_malha_bairros

    return Localizador(geo_local(), carregar_malha_bairros())


@functools.lru_cache(maxsize=1)
def contorno_recife():
    from climasense.territorio.carga import geo_local
    from climasense.territorio.geometria import contorno_recife as contorno

    return contorno(geo_local())


def gravar_estacoes(c, fonte_id: str, estacoes: list[dict]) -> int:
    """Upsert em silver.estacoes (id, codigo_fonte, nome, lat, lon, territorio_id)."""
    if not estacoes:
        return 0
    c.execute(
        text(
            "insert into silver.estacoes (id, fonte_id, codigo_fonte, nome, lat, lon, territorio_id, ativa) "
            "values (:id, :f, :codigo, :nome, :lat, :lon, :territorio_id, true) on conflict (id) do update set "
            "nome = excluded.nome, lat = excluded.lat, lon = excluded.lon, territorio_id = excluded.territorio_id, "
            "ativa = true"
        ),
        [{**e, "f": fonte_id} for e in estacoes],
    )
    return len(estacoes)
