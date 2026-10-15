"""Proteção contra força bruta (RF-02.3): 5 falhas em 15 minutos bloqueiam a conta por 15 minutos.
Domínio puro: recebe as tentativas e o relógio, devolve até quando está bloqueado."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

LIMITE_FALHAS = 5
JANELA = timedelta(minutes=15)
DURACAO_BLOQUEIO = timedelta(minutes=15)


@dataclass(frozen=True)
class Tentativa:
    em: datetime
    sucesso: bool


def bloqueado_ate(tentativas: Iterable[Tentativa], agora: datetime) -> datetime | None:
    """Conta as falhas desde o último sucesso; se a 5ª falha caiu numa janela de 15 min, bloqueia por 15 min."""
    falhas: list[datetime] = []
    for t in sorted(tentativas, key=lambda t: t.em):
        if t.sucesso:
            falhas.clear()
        else:
            falhas.append(t.em)
            falhas = [f for f in falhas if t.em - f < JANELA]
            if len(falhas) >= LIMITE_FALHAS:
                fim = t.em + DURACAO_BLOQUEIO
                if fim > agora:
                    return fim
                falhas.clear()
    return None
