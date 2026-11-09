"""Aquecimento do cache em memória (infra/cache.py): mantém quentes as leituras que as telas pedem primeiro.

Com o banco a ~150 ms por consulta, a primeira leitura depois que um cache vence custa segundos. Em vez de a pessoa
pagar isso, o servidor refaz estas leituras em segundo plano um pouco antes de o TTL vencer (`INTERVALO_S` < TTL
vivo). Só LEITURAS agregadas, iguais para todos; nada é gravado. Cada passo falha sozinho (um erro não derruba os
outros nem a API) e só o tipo do erro vai para o log (mensagens de driver podem ter a URI).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime

from sqlalchemy.orm import Session

from climasense.infra import cache
from climasense.servicos import (
    estagios,
    prioridade_vulnerabilidade,
    saude_agravos,
    situacao_chuva,
    vulnerabilidade,
)
from climasense.servicos import fontes as servico_fontes
from climasense.servicos import simulador as servico_simulador

log = logging.getLogger("climasense.aquecimento")
INTERVALO_S = 45.0  # abaixo do TTL vivo (60 s): o cache nunca chega a vencer em uso normal
assert INTERVALO_S < cache.VIVO_S


def passos(db: Session, agora: datetime) -> list[tuple[str, Callable[[], object]]]:
    return [
        ("fontes", lambda: servico_fontes.linhas(db, agora)),
        ("estagios", lambda: estagios.listar(db, "distrito", agora)),
        ("premissas", lambda: servico_simulador.premissas_atuais(db, agora)),
        ("situacao", lambda: situacao_chuva.montar(db, agora)),
        (
            "prioridade",
            lambda: [prioridade_vulnerabilidade.listar(db, n) for n in ("distrito", "bairro", None)],
        ),
        ("saude", lambda: saude_agravos.resumo_agravos(db, agora)),
        (
            "saude_semanal",
            lambda: [saude_agravos.semanal(db, a, None, agora) for a in saude_agravos.AGRAVOS],
        ),
        ("vulnerabilidade", lambda: vulnerabilidade.vulneraveis_por_territorio(db)),
    ]


def aquecer(fabrica_sessao: Callable[[], Session], agora: datetime) -> dict[str, bool]:
    """Roda cada passo com a própria sessão. Devolve passo → deu certo."""
    resultado: dict[str, bool] = {}
    with fabrica_sessao() as sondagem:
        nomes = [n for n, _ in passos(sondagem, agora)]
    for i, nome in enumerate(nomes):
        try:
            with fabrica_sessao() as db, cache.renovando():
                passos(db, agora)[i][1]()
            resultado[nome] = True
        except Exception as erro:  # noqa: BLE001 — só o tipo: mensagens de driver podem ter a URI
            log.warning("Aquecimento do cache '%s' falhou (%s)", nome, type(erro).__name__)
            resultado[nome] = False
    return resultado
