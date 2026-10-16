"""Regras do território (domínio puro): busca sem acento, igual ao `normalize` do model.js da Aula 07."""

from __future__ import annotations

import unicodedata


def normalizar_busca(valor: str) -> str:
    return (
        "".join(c for c in unicodedata.normalize("NFD", str(valor)) if unicodedata.category(c) != "Mn")
        .lower()
        .strip()
    )
