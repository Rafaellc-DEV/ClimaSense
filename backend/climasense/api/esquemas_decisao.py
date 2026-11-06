"""Esquemas das respostas de apoio à decisão: situação agora, prioridades e ações (painel de gestão)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

StatusIndicador = Literal["ok", "dados_insuficientes"]
NivelPrioridade = Literal["sem_indicacao", "atencao", "alerta", "critico", "dados_insuficientes"]
Confianca = Literal["media", "baixa", "insuficiente"]


class FatorRisco(BaseModel):
    nome: str
    descricao: str


class JanelaRisco(BaseModel):
    inicio: datetime
    fim: datetime


class MotivoPrioridade(BaseModel):
    ordem: int
    fator: str
    descricao: str
    origem: Literal["estimador", "aviso", "avaliacao", "ocorrencias", "qualidade"]


class EvidenciaPrioridade(BaseModel):
    tipo: Literal["cenario", "serie", "mapa"]
    rotulo: str
    fonte_id: str
    endereco: str
    parametros: dict[str, str]


class ItemPrioridade(BaseModel):
    posicao: int
    territorio_id: str
    territorio_nome: str
    tipo: Literal["distrito", "bairro"]
    distrito_id: str
    nivel: NivelPrioridade
    rotulo: str
    nivel_estimador: NivelPrioridade
    nivel_equipe: str | None
    experimental: Literal[True] = True
    confianca: Confianca
    motivos: list[MotivoPrioridade]
    notas_qualidade: list[str]
    evidencias: list[EvidenciaPrioridade]
    janela_atencao: JanelaRisco | None
    acumulado_previsto_mm: float | None
    limite_atencao_mm: float | None
    limite_alerta_mm: float | None
    ocorrencias_historicas: int | None


class Prioridades(BaseModel):
    nivel_territorial: Literal["distrito", "bairro"]
    horizonte_h: int
    gerado_em: datetime
    total: int
    resumo: str
    itens: list[ItemPrioridade]
