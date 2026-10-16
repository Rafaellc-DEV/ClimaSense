"""Interface do estimador de alagamento (design §5.5). O modelo de ML real entra numa etapa própria e só
precisa implementar este protocolo; a tela de cenários não muda."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from climasense.dominio import cenario


class EstimadorAlagamento(Protocol):
    metodo: str
    versao: str
    experimental: bool

    def estimar(
        self, territorio_id: str, horizonte_h: int, insumos: cenario.Insumos, agora: datetime
    ) -> cenario.Estimativa: ...


class EstimadorReferencia:
    """Regra simples e transparente sobre dados reais (dominio/cenario.py). Sempre experimental (RN-11)."""

    metodo = cenario.METODO
    versao = cenario.VERSAO
    experimental = True

    def estimar(
        self, territorio_id: str, horizonte_h: int, insumos: cenario.Insumos, agora: datetime
    ) -> cenario.Estimativa:
        return cenario.estimar(insumos, horizonte_h, agora)
