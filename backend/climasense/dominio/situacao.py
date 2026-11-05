"""Situação agora (decisão rápida): chuva recente contra a referência do período e pico previsto.
Domínio puro, sem I/O. Falta de dado nunca vira zero (RN-01, RN-02)."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class Janela:
    horas: int
    acumulado_mm: float | None
    horas_com_dado: int

    @property
    def cobertura_pct(self) -> float:
        return round(100 * self.horas_com_dado / self.horas, 1)


def acumulado_recente(por_hora: dict[datetime, float | None], fim: datetime, horas: int) -> Janela:
    """Soma das `horas` horas cheias que terminam em `fim`. Só devolve o total se TODAS as horas têm dado:
    um total parcial subestimaria a chuva e pareceria um valor real."""
    fim = fim.replace(minute=0, second=0, microsecond=0)
    esperadas = [fim - timedelta(hours=i) for i in range(1, horas + 1)]
    valores = [por_hora.get(h) for h in esperadas]
    com_dado = [v for v in valores if v is not None]
    total = round(sum(com_dado), 1) if len(com_dado) == horas else None
    return Janela(horas=horas, acumulado_mm=total, horas_com_dado=len(com_dado))


@dataclass(frozen=True)
class ComparacaoReferencia:
    referencia_mm: float
    razao_pct: float
    texto: str


def comparar_com_referencia(
    acumulado_mm: float | None, media_mensal_mm: float | None, ano: int, mes: int, horas: int
) -> ComparacaoReferencia | None:
    """Compara com o que se espera em `horas` horas no mês, segundo a média histórica mensal."""
    if acumulado_mm is None or media_mensal_mm is None:
        return None
    dias_no_mes = calendar.monthrange(ano, mes)[1]
    esperado = media_mensal_mm / dias_no_mes * (horas / 24)
    if esperado <= 0:
        return None
    razao = round(100 * acumulado_mm / esperado, 0)
    if razao >= 200:
        texto = f"Mais que o dobro do esperado para o mês ({razao:.0f}% da média)."
    elif razao >= 120:
        texto = f"Acima do esperado para o mês ({razao:.0f}% da média)."
    elif razao >= 80:
        texto = f"Perto do esperado para o mês ({razao:.0f}% da média)."
    else:
        texto = f"Abaixo do esperado para o mês ({razao:.0f}% da média)."
    return ComparacaoReferencia(round(esperado, 1), razao, texto)


def pico_previsto(
    chuva: list[tuple[datetime, float | None]], inicio: datetime, horas: int = 72
) -> tuple[datetime, float] | None:
    """Hora de maior chuva prevista no horizonte; None se não há nenhuma hora com dado."""
    limite = inicio + timedelta(hours=horas)
    validas = [(t, v) for t, v in chuva if inicio <= t < limite and v is not None]
    if not validas:
        return None
    return max(validas, key=lambda p: p[1])
