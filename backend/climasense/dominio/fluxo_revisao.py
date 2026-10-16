"""Fluxo de revisão de avaliações e comunicados (design §7.1, RF-10, RF-11). Domínio puro.

A tabela TRANSICOES é a fonte da verdade: (alvo, estado, ação) → (novo estado, permissão exigida).
As guardas aplicam as regras que não cabem na tabela:

- RN-03: editar sempre cria uma versão nova; uma versão revisada nunca é sobrescrita;
- RN-04: só publica a mesma versão que foi aprovada;
- RN-05: quem escreveu a versão não a aprova nem a devolve (vale para qualquer papel);
- RN-14: só publica com validade definida e ainda não vencida;
- devolver exige justificativa (RF-10.3).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from climasense.dominio.papeis import Permissao, pode


class Alvo(StrEnum):
    AVALIACAO = "avaliacao"
    COMUNICADO = "comunicado"


class Estado(StrEnum):
    RASCUNHO = "rascunho"
    EM_REVISAO = "em_revisao"
    APROVADO = "aprovado"
    DEVOLVIDO = "devolvido"
    PUBLICADO = "publicado"
    ENCERRADO = "encerrado"


class Acao(StrEnum):
    EDITAR = "editar"
    ENVIAR = "enviar"
    APROVAR = "aprovar"
    DEVOLVER = "devolver"
    PUBLICAR = "publicar"
    ENCERRAR = "encerrar"


E, A, P = Estado, Acao, Permissao
_COMUNS: dict[tuple[Estado, Acao], tuple[Estado, Permissao]] = {
    (E.RASCUNHO, A.EDITAR): (E.RASCUNHO, P.EDITAR),
    (E.DEVOLVIDO, A.EDITAR): (E.RASCUNHO, P.EDITAR),
    (E.EM_REVISAO, A.EDITAR): (E.EM_REVISAO, P.EDITAR),  # ajuste: a versão nova precisa de nova revisão
    (E.APROVADO, A.EDITAR): (E.EM_REVISAO, P.EDITAR),  # RN-03: a aprovação era da versão anterior
    (E.RASCUNHO, A.ENVIAR): (E.EM_REVISAO, P.EDITAR),
    (E.EM_REVISAO, A.APROVAR): (E.APROVADO, P.REVISAR),
    (E.EM_REVISAO, A.DEVOLVER): (E.DEVOLVIDO, P.REVISAR),
}
_ENCERRAR_DE = (E.RASCUNHO, E.EM_REVISAO, E.APROVADO, E.DEVOLVIDO)

TRANSICOES: dict[tuple[Alvo, Estado, Acao], tuple[Estado, Permissao]] = {
    **{(Alvo.AVALIACAO, e, a): v for (e, a), v in _COMUNS.items()},
    **{(Alvo.AVALIACAO, e, A.ENCERRAR): (E.ENCERRADO, P.PUBLICAR) for e in _ENCERRAR_DE},
    **{(Alvo.COMUNICADO, e, a): v for (e, a), v in _COMUNS.items()},
    (Alvo.COMUNICADO, E.APROVADO, A.PUBLICAR): (E.PUBLICADO, P.PUBLICAR),
    (Alvo.COMUNICADO, E.PUBLICADO, A.EDITAR): (E.EM_REVISAO, P.EDITAR),  # sai da landing até nova aprovação
    **{(Alvo.COMUNICADO, e, A.ENCERRAR): (E.ENCERRADO, P.PUBLICAR) for e in (*_ENCERRAR_DE, E.PUBLICADO)},
}

ROTULOS_ESTADO = {
    E.RASCUNHO: "Rascunho",
    E.EM_REVISAO: "Em revisão",
    E.APROVADO: "Aprovado",
    E.DEVOLVIDO: "Devolvido",
    E.PUBLICADO: "Publicado",
    E.ENCERRADO: "Encerrado",
}
_VERBOS = {
    A.EDITAR: "editar",
    A.ENVIAR: "enviar para revisão",
    A.APROVAR: "aprovar",
    A.DEVOLVER: "devolver",
    A.PUBLICAR: "publicar",
    A.ENCERRAR: "encerrar",
}


class TransicaoNegada(Exception):
    """Ação não permitida, com a mensagem pronta para a tela e o status HTTP correspondente."""

    def __init__(self, status: int, mensagem: str) -> None:
        super().__init__(mensagem)
        self.status = status
        self.mensagem = mensagem


@dataclass(frozen=True)
class Situacao:
    alvo: Alvo
    estado: Estado
    autor_versao_atual: str
    versao_atual: int
    versao_aprovada: int | None = None
    validade_fim: datetime | None = None


def acoes_possiveis(s: Situacao, ator_id: str, papeis: list[str], agora: datetime) -> list[Acao]:
    """As ações que esta pessoa pode fazer agora (a interface só mostra estas — e a API confere de novo)."""
    possiveis = []
    for acao in Acao:
        try:
            aplicar(s, acao, ator_id, papeis, agora, justificativa="(verificação)")
        except TransicaoNegada:
            continue
        possiveis.append(acao)
    return possiveis


def aplicar(
    s: Situacao,
    acao: Acao,
    ator_id: str,
    papeis: list[str],
    agora: datetime,
    justificativa: str | None = None,
) -> Estado:
    """Novo estado, ou TransicaoNegada explicando o motivo. Não altera nada: só decide."""
    destino = TRANSICOES.get((s.alvo, s.estado, acao))
    if destino is None:
        raise TransicaoNegada(
            409,
            f"Não é possível {_VERBOS[acao]} um item no estado “{ROTULOS_ESTADO[s.estado]}”.",
        )
    novo, permissao = destino
    if not pode(papeis, permissao):
        raise TransicaoNegada(403, "Você não tem permissão para esta ação. Fale com a coordenação.")
    if acao is A.ENVIAR and ator_id != s.autor_versao_atual:
        raise TransicaoNegada(403, "Só quem escreveu a versão atual pode enviá-la para revisão.")
    if acao in (A.APROVAR, A.DEVOLVER) and ator_id == s.autor_versao_atual:
        raise TransicaoNegada(403, "Você escreveu esta versão. Outra pessoa precisa revisá-la.")
    if acao is A.DEVOLVER and not (justificativa or "").strip():
        raise TransicaoNegada(422, "Escreva o motivo da devolução, para quem escreveu saber o que ajustar.")
    if acao is A.PUBLICAR:
        if s.versao_aprovada != s.versao_atual:
            raise TransicaoNegada(
                409, "Só a versão aprovada pode ser publicada. Envie a versão atual para revisão."
            )
        if s.validade_fim is None:
            raise TransicaoNegada(422, "Defina até quando o aviso vale antes de publicar.")
        if s.validade_fim <= agora:
            raise TransicaoNegada(
                422, "A validade deste aviso já terminou. Edite a validade e envie para revisão."
            )
    return novo
