"""Prioridades de atenção entre territórios (apoio à decisão). Domínio puro, EXPERIMENTAL (RN-11).

Ordem: níveis com indicação (crítico, alerta, atenção) → dados insuficientes → sem indicação.
Quem não tem dado suficiente não é tratado como seguro: aparece antes de “sem indicação”, com o motivo.
A prioridade é uma indicação para avaliar, nunca uma probabilidade (RN-06).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Nivel = Literal["sem_indicacao", "atencao", "alerta", "critico", "dados_insuficientes"]
Confianca = Literal["media", "baixa", "insuficiente"]

PESO: dict[str, int] = {"sem_indicacao": 0, "atencao": 1, "alerta": 2, "critico": 3}
# nível do aviso/avaliação da equipe → escada do estimador
DO_AVISO = {"informativo": "sem_indicacao", "atencao": "atencao", "alerta": "alerta", "critico": "critico"}
ROTULO = {
    "sem_indicacao": "Sem indicação",
    "atencao": "Atenção",
    "alerta": "Alerta",
    "critico": "Situação crítica",
    "dados_insuficientes": "Dados insuficientes",
}


@dataclass
class Motivo:
    fator: str
    descricao: str
    origem: str  # estimador | aviso | avaliacao | ocorrencias | qualidade
    peso: int = 0  # maior = mais importante na lista


@dataclass
class Candidato:
    territorio_id: str
    nivel_estimador: Nivel
    nivel_equipe: str | None = None  # maior nível entre avisos vigentes e avaliações em curso
    intensidade: float = 0.0  # acumulado previsto / limite de atenção (desempate)
    ocorrencias: int | None = None
    motivos: list[Motivo] = field(default_factory=list)


def nivel_efetivo(c: Candidato) -> Nivel:
    equipe = c.nivel_equipe if c.nivel_equipe in PESO else None
    if c.nivel_estimador == "dados_insuficientes":
        return equipe if equipe and PESO[equipe] > 0 else "dados_insuficientes"  # type: ignore[return-value]
    if equipe and PESO[equipe] > PESO[c.nivel_estimador]:
        return equipe  # type: ignore[return-value]
    return c.nivel_estimador


def confianca(qualidade: str, emissoes_na_faixa: int, fontes_com_problema: int) -> Confianca:
    """Nunca “alta”: a regra de referência não foi validada. Cada fragilidade rebaixa um degrau."""
    if qualidade == "insuficiente":
        return "insuficiente"
    pontos = 1  # base “média”
    if qualidade == "parcial":
        pontos -= 1
    if emissoes_na_faixa < 2:
        pontos -= 1
    if fontes_com_problema:
        pontos -= 1
    return "media" if pontos >= 1 else "baixa"


def chave_ordem(c: Candidato) -> tuple:
    nivel = nivel_efetivo(c)
    grupo = 0 if PESO.get(nivel, 0) > 0 else (1 if nivel == "dados_insuficientes" else 2)
    return (grupo, -PESO.get(nivel, 0), -c.intensidade, -(c.ocorrencias or 0), c.territorio_id)


def ordenar(candidatos: list[Candidato]) -> list[Candidato]:
    return sorted(candidatos, key=chave_ordem)


def motivos_ordenados(c: Candidato) -> list[Motivo]:
    return sorted(c.motivos, key=lambda m: -m.peso)
