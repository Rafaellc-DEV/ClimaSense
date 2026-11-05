"""Abrigos e desabrigados (F3). Domínio puro: validação e totais do topo do painel.

Contagem não informada é ausente, não zero (RN-02): o total só soma o que foi informado e diz quantos abrigos
ficaram sem contagem.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

CAMPOS_HISTORICO = (
    "nome",
    "endereco",
    "capacidade",
    "aberto",
    "pessoas_abrigadas",
    "desabrigados",
    "observacao",
    "latitude",
    "longitude",
)


@dataclass(frozen=True)
class SituacaoAbrigo:
    aberto: bool
    pessoas_abrigadas: int | None
    desabrigados: int | None
    atualizado_em: datetime | None


@dataclass(frozen=True)
class Totais:
    abrigos_abertos: int
    abrigos_cadastrados: int
    pessoas_abrigadas: int | None  # soma nos abrigos ABERTOS (quem está lá agora)
    desabrigados: int | None  # soma de todos os abrigos (atendidos no evento, inclusive os já fechados)
    abertos_sem_contagem: int  # abertos sem o número de pessoas abrigadas
    atualizado_em: datetime | None


def _soma(valores: list[int | None]) -> int | None:
    informados = [v for v in valores if v is not None]
    return sum(informados) if informados else None


def totais(abrigos: list[SituacaoAbrigo]) -> Totais:
    abertos = [a for a in abrigos if a.aberto]
    datas = [a.atualizado_em for a in abrigos if a.atualizado_em]
    return Totais(
        abrigos_abertos=len(abertos),
        abrigos_cadastrados=len(abrigos),
        pessoas_abrigadas=_soma([a.pessoas_abrigadas for a in abertos]),
        desabrigados=_soma([a.desabrigados for a in abrigos]),
        abertos_sem_contagem=sum(1 for a in abertos if a.pessoas_abrigadas is None),
        atualizado_em=max(datas) if datas else None,
    )


def problemas(
    nome: str | None, capacidade: int | None, pessoas_abrigadas: int | None, desabrigados: int | None
) -> list[str]:
    erros = []
    if nome is not None and not nome.strip():
        erros.append("Escreva o nome do abrigo.")
    for rotulo, v in (
        ("A capacidade", capacidade),
        ("O número de pessoas abrigadas", pessoas_abrigadas),
        ("O número de desabrigados", desabrigados),
    ):
        if v is not None and v < 0:
            erros.append(f"{rotulo} não pode ser negativo.")
    return erros


def alteracoes(antes: dict, depois: dict) -> dict[str, dict]:
    """Campos que mudaram: {campo: {"de": ..., "para": ...}} (histórico de cada atualização)."""
    return {
        c: {"de": antes.get(c), "para": depois.get(c)}
        for c in CAMPOS_HISTORICO
        if c in depois and antes.get(c) != depois.get(c)
    }
