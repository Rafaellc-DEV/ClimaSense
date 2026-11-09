"""Limites de frescor por fonte (RF-19, RNF-05), lidos de `frescor.toml`.

Funcoes puras: nao tocam banco nem rede. Ausencia de dado nunca e tratada como "em dia" (RN-01).
"""

from __future__ import annotations

import tomllib
from datetime import datetime
from functools import lru_cache
from pathlib import Path

ARQUIVO = Path(__file__).with_name("frescor.toml")


@lru_cache(maxsize=1)
def limites() -> dict[str, float]:
    """Limites em horas por fonte_id; fontes sem limite (valor 0 ou ausente) ficam de fora."""
    with ARQUIVO.open("rb") as f:
        bruto = tomllib.load(f).get("limites_h", {})
    return {fonte: float(h) for fonte, h in bruto.items() if h and h > 0}


@lru_cache(maxsize=1)
def fontes_sem_limite() -> frozenset[str]:
    """Fontes listadas no TOML com valor 0: estáticas de propósito (território, Censo). Nunca ficam desatualizadas."""
    with ARQUIVO.open("rb") as f:
        bruto = tomllib.load(f).get("limites_h", {})
    return frozenset(fonte for fonte, h in bruto.items() if not h or h <= 0)


def limite_frescor_h(fonte_id: str) -> float | None:
    """Horas alem das quais o dado da fonte e desatualizado; None se a fonte nao tem limite."""
    return limites().get(fonte_id)


def esta_desatualizado(fonte_id: str, atualizado_em: datetime | None, agora: datetime) -> bool | None:
    """True/False conforme a idade do dado; None se nao ha dado ou nao ha limite (nunca "em dia")."""
    limite = limite_frescor_h(fonte_id)
    if atualizado_em is None or limite is None:
        return None
    if (atualizado_em.tzinfo is None) != (agora.tzinfo is None):
        raise ValueError("atualizado_em e agora precisam ser ambos com fuso ou ambos sem fuso")
    return (agora - atualizado_em).total_seconds() / 3600 > limite
