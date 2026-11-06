"""Abrigos e desabrigados (F3). Domínio puro: validação e totais do topo do painel.

Contagem não informada é ausente, não zero (RN-02): o total só soma o que foi informado e diz quantos abrigos
ficaram sem contagem.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

MAXIMO_PESSOAS = 100_000
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


@dataclass(frozen=True)
class TotaisSituacao:
    """Totais de um recorte (cidade ou distrito) para a situação do evento (RF-08, RF-09)."""

    abrigos_abertos: int | None  # null: nenhum abrigo cadastrado no recorte (nada sabido)
    abrigos_cadastrados: int
    pessoas_abrigadas: int | None
    desabrigados: int | None
    parcial: bool  # há abrigo aberto sem contagem: o total sairia subestimado, então fica null
    abertos_sem_contagem: int
    atualizado_em: datetime | None


def totais_situacao(abrigos: list[SituacaoAbrigo]) -> TotaisSituacao:
    """Ausência não é zero (RN-01, RN-02). Sem abrigo cadastrado tudo é null. Com abrigos mas nenhum aberto, as
    pessoas abrigadas são 0 (derivado). Abrigo aberto sem contagem torna o total null e `parcial`."""
    if not abrigos:
        return TotaisSituacao(None, 0, None, None, False, 0, None)
    base = totais(abrigos)
    abertos = [a for a in abrigos if a.aberto]
    if not abertos:
        abrigadas = 0
    elif base.abertos_sem_contagem:
        abrigadas = None
    else:
        abrigadas = _soma([a.pessoas_abrigadas for a in abertos])
    abertos_sem_desabrigados = sum(1 for a in abertos if a.desabrigados is None)
    return TotaisSituacao(
        abrigos_abertos=base.abrigos_abertos,
        abrigos_cadastrados=base.abrigos_cadastrados,
        pessoas_abrigadas=abrigadas,
        desabrigados=None if abertos_sem_desabrigados else base.desabrigados,
        parcial=bool(base.abertos_sem_contagem or abertos_sem_desabrigados),
        abertos_sem_contagem=base.abertos_sem_contagem,
        atualizado_em=base.atualizado_em,
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
        elif v is not None and v > MAXIMO_PESSOAS:
            erros.append(f"{rotulo} não pode passar de {MAXIMO_PESSOAS:,}.".replace(",", "."))
    return erros


def alteracoes(antes: dict, depois: dict) -> dict[str, dict]:
    """Campos que mudaram: {campo: {"de": ..., "para": ...}} (histórico de cada atualização)."""
    return {
        c: {"de": antes.get(c), "para": depois.get(c)}
        for c in CAMPOS_HISTORICO
        if c in depois and antes.get(c) != depois.get(c)
    }
