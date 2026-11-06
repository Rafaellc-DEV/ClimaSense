"""Supressão de células pequenas (RNF-03, RN-13). Domínio puro.

Contagem de agravo por território com valor entre 1 e `minimo - 1` poderia identificar uma pessoa: sai como nula e
marcada como suprimida. Zero medido continua zero (RN-02): não identifica ninguém e é informação.
"""

from __future__ import annotations


def deve_suprimir(valor: int | None, minimo: int) -> bool:
    return valor is not None and 0 < valor < minimo


def suprimir(valor: int | None, minimo: int) -> tuple[int | None, bool]:
    """(valor publicável, suprimido)."""
    return (None, True) if deve_suprimir(valor, minimo) else (valor, False)
