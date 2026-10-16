"""Séries de chuva a partir da gold (RF-08). As agregações por período e o resumo vêm do domínio."""

from __future__ import annotations

from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

FONTE_CHUVA = "open-meteo-historico"


def chuva_diaria(db: Session, territorio_id: str, inicio: date, fim: date) -> dict[date, float | None]:
    linhas = db.execute(
        text(
            "select dia, acumulado_mm from gold.chuva_diaria where territorio_id = :t and tipo = 'derivada' "
            "and dia between :i and :f"
        ),
        {"t": territorio_id, "i": inicio, "f": fim},
    ).all()
    return {d: v for d, v in linhas}


def referencia(db: Session, territorio_id: str) -> list[dict]:
    return [
        dict(r)
        for r in db.execute(
            text(
                "select mes_do_ano, media_mm, mediana_mm, anos_usados, cobertura_pct from gold.referencia_mensal "
                "where territorio_id = :t order by mes_do_ano"
            ),
            {"t": territorio_id},
        ).mappings()
    ]


def mensal(db: Session, territorio_id: str) -> list[dict]:
    return [
        dict(r)
        for r in db.execute(
            text(
                "select mes, acumulado_mm, dias_com_dado, cobertura_pct from gold.chuva_mensal "
                "where territorio_id = :t and tipo = 'derivada' order by mes"
            ),
            {"t": territorio_id},
        ).mappings()
    ]
