"""Risco de alagamento por bairro e dia (F6, specs/foco-chuvas.md). EXPERIMENTAL (RN-11).

Árvore de decisão com validação temporal; rótulo = atendimentos de alagamento da Defesa Civil do Recife
(Dados Abertos); atributos = chuva ERA5 do distrito, maré astronômica, mês e histórico do bairro.
Treino e relatório: `python -m climasense.ml alagamento`. Uso no produto: `risco_por_territorio`.
"""

from __future__ import annotations

from datetime import datetime


def risco_por_territorio(db, agora: datetime) -> dict[str, dict]:
    """territorio_id (bairro) → {"classe": baixo|moderado|alto|sem_dados, "fatores": [str]}.

    Devolve `{}` quando não há modelo publicado (o gatilho de estágio ignora este insumo).
    """
    from climasense.ml.alagamento.servico import risco_por_territorio as _risco

    return _risco(db, agora)
