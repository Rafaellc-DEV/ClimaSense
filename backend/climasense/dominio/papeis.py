"""Papéis e permissões (RF-03, requirements §3). Domínio puro.

Permissões são cumulativas: revisor faz tudo do analista; coordenação, tudo do revisor.
O administrador gerencia o sistema e também tem acesso completo; a regra “ninguém aprova o próprio
conteúdo” (RN-05) vale para qualquer papel e é aplicada no fluxo de revisão, não aqui.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum


class Papel(StrEnum):
    ANALISTA = "analista"
    REVISOR = "revisor"
    COORDENACAO = "coordenacao"
    ADMINISTRADOR = "administrador"


class Permissao(StrEnum):
    CONSULTAR = "consultar"  # painéis, mapa, séries, cenários, fontes
    EDITAR = "editar"  # avaliações e rascunhos de comunicado
    REVISAR = "revisar"  # aprovar ou devolver versões
    PUBLICAR = "publicar"  # publicar e encerrar comunicados aprovados
    ADMINISTRAR = "administrar"  # usuários, papéis, auditoria, fontes
    EXECUTAR_ETL = "executar_etl"


_BASE = {Permissao.CONSULTAR, Permissao.EDITAR}
PERMISSOES: dict[Papel, frozenset[Permissao]] = {
    Papel.ANALISTA: frozenset(_BASE),
    Papel.REVISOR: frozenset(_BASE | {Permissao.REVISAR}),
    Papel.COORDENACAO: frozenset(_BASE | {Permissao.REVISAR, Permissao.PUBLICAR}),
    Papel.ADMINISTRADOR: frozenset(Permissao),
}

DESCRICOES: dict[Papel, str] = {
    Papel.ANALISTA: "Consulta os dados, registra avaliações e escreve rascunhos de comunicado.",
    Papel.REVISOR: "Tudo do analista, e também aprova ou devolve avaliações e comunicados de outras pessoas.",
    Papel.COORDENACAO: "Tudo do revisor, e também publica e encerra comunicados aprovados.",
    Papel.ADMINISTRADOR: "Gerencia contas, papéis, fontes de dados e a auditoria.",
}

MENSAGEM_SEM_PERMISSAO = "Você não tem permissão para esta ação. Fale com a coordenação."


class PapelInvalido(ValueError):
    pass


def normalizar(papeis: Iterable[str]) -> list[Papel]:
    """Valida e ordena os papéis, sem repetição. Pelo menos um papel é obrigatório."""
    vistos: list[Papel] = []
    for p in papeis:
        try:
            papel = Papel(p)
        except ValueError:
            raise PapelInvalido(
                f"Papel “{p}” não existe. Use: analista, revisor, coordenacao ou administrador."
            ) from None
        if papel not in vistos:
            vistos.append(papel)
    if not vistos:
        raise PapelInvalido("Escolha pelo menos um papel para a conta.")
    return sorted(vistos, key=list(Papel).index)


def permissoes(papeis: Iterable[str]) -> frozenset[Permissao]:
    resultado: set[Permissao] = set()
    for p in normalizar(papeis):
        resultado |= PERMISSOES[p]
    return frozenset(resultado)


def pode(papeis: Iterable[str], permissao: Permissao) -> bool:
    try:
        return permissao in permissoes(papeis)
    except PapelInvalido:
        return False
