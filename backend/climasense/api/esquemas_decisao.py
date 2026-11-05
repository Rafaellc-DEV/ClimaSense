"""Esquemas das respostas de apoio à decisão: situação agora, prioridades e ações (painel de gestão)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

StatusIndicador = Literal["ok", "dados_insuficientes"]
NivelPrioridade = Literal["sem_indicacao", "atencao", "alerta", "critico", "dados_insuficientes"]
Confianca = Literal["media", "baixa", "insuficiente"]


class ChuvaRecente(BaseModel):
    janela_h: int
    status: StatusIndicador
    acumulado_mm: float | None
    horas_com_dado: int
    cobertura_pct: float
    referencia_mm: float | None
    razao_referencia_pct: float | None
    comparacao: str | None
    ate_em: datetime
    fontes_usadas: list[str]
    nota: str | None


class PicoPrevisto(BaseModel):
    horizonte_h: int
    status: StatusIndicador
    valor_mm: float | None
    em: datetime | None
    maior_24h_mm: float | None
    limite_atencao_mm: float | None
    limite_alerta_mm: float | None
    emitida_em: datetime | None
    fonte_id: str
    nota: str | None


class MarePrevista(BaseModel):
    status: StatusIndicador
    maxima_m: float | None
    maxima_em: datetime | None
    emitida_em: datetime | None
    fonte_id: str
    nota: str | None


class FatorRisco(BaseModel):
    nome: str
    descricao: str


class JanelaRisco(BaseModel):
    inicio: datetime
    fim: datetime


class RiscoGeral(BaseModel):
    prioridade: NivelPrioridade
    rotulo: str
    motivo: str
    fatores: list[FatorRisco]
    limitacoes: list[str]
    qualidade: Literal["completa", "parcial", "insuficiente"]
    confianca: Confianca
    janela_atencao: JanelaRisco | None
    horizonte_h: int
    metodo: str
    versao_metodo: str
    experimental: Literal[True] = True
    emitida_em: datetime


class FrescorFonte(BaseModel):
    fonte_id: str
    nome: str
    status: str
    ultimo_sucesso: datetime | None
    idade_h: float | None
    limite_h: int


class SituacaoAgora(BaseModel):
    territorio_id: str
    territorio_nome: str
    gerado_em: datetime
    chuva_24h: ChuvaRecente
    chuva_72h: ChuvaRecente
    pico: PicoPrevisto
    mare: MarePrevista
    risco: RiscoGeral
    frescor: list[FrescorFonte]


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


class AcaoAgora(BaseModel):
    urgencia: Literal["alta", "media", "baixa"]
    tipo: str
    titulo: str
    detalhe: str
    endereco: str


class AcoesAgora(BaseModel):
    gerado_em: datetime
    itens: list[AcaoAgora]
    nota: str | None = None
