"""Adaptador para o serviço de estágios (backend): mesmo formato de `GET /risco-alagamento`.

    {"disponivel": bool, "motivo": str | None, "modelo": {...} | None,
     "itens": [{"territorio_id", "classe", "fatores": [str]}]}

Classes: `baixo`, `moderado`, `alto`, `sem_dados`. Experimental (RN-11), nunca probabilidade (RN-06).
"""

from __future__ import annotations

from datetime import datetime


def risco_por_bairro(db, agora: datetime) -> dict:
    from climasense.ml.alagamento.servico import payload

    return payload(db, agora, nivel="bairro")
