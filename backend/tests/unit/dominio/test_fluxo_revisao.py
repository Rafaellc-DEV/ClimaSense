"""T7.1 — teste EXAUSTIVO do fluxo de revisão: todo alvo × estado × ação × papel × (autor ou não).

O resultado esperado é escrito aqui de forma independente, direto do design §7.1 e das regras RN-03/04/05/14,
e comparado com `fluxo_revisao.aplicar`.
"""

from __future__ import annotations

import itertools
from datetime import UTC, datetime, timedelta

import pytest

from climasense.dominio.fluxo_revisao import (
    Acao,
    Alvo,
    Estado,
    Situacao,
    TransicaoNegada,
    acoes_possiveis,
    aplicar,
)
from climasense.dominio.papeis import Papel

AGORA = datetime(2026, 10, 15, 20, 0, tzinfo=UTC)
AUTOR, OUTRO = "autor", "outra-pessoa"

# design §7.1 — (estado, ação) → novo estado. Avaliações não têm “publicado”.
GRAFO = {
    ("rascunho", "editar"): "rascunho",
    ("devolvido", "editar"): "rascunho",
    ("em_revisao", "editar"): "em_revisao",
    ("aprovado", "editar"): "em_revisao",
    ("publicado", "editar"): "em_revisao",
    ("rascunho", "enviar"): "em_revisao",
    ("em_revisao", "aprovar"): "aprovado",
    ("em_revisao", "devolver"): "devolvido",
    ("aprovado", "publicar"): "publicado",
    **{
        (e, "encerrar"): "encerrado" for e in ("rascunho", "em_revisao", "aprovado", "devolvido", "publicado")
    },
}
QUEM = {  # quais papéis podem cada ação (permissões cumulativas; o administrador pode tudo)
    "editar": {"analista", "revisor", "coordenacao", "administrador"},
    "enviar": {"analista", "revisor", "coordenacao", "administrador"},
    "aprovar": {"revisor", "coordenacao", "administrador"},
    "devolver": {"revisor", "coordenacao", "administrador"},
    "publicar": {"coordenacao", "administrador"},
    "encerrar": {"coordenacao", "administrador"},
}


def esperado(alvo: str, estado: str, acao: str, papel: str, ator: str) -> str | int:
    """Novo estado, ou o status HTTP da recusa."""
    if alvo == "avaliacao" and "publicado" in (estado, GRAFO.get((estado, acao))):
        return 409
    if (estado, acao) not in GRAFO:
        return 409
    if papel not in QUEM[acao]:
        return 403
    if acao == "enviar" and ator != AUTOR:
        return 403
    if acao in ("aprovar", "devolver") and ator == AUTOR:
        return 403  # RN-05
    return GRAFO[(estado, acao)]


CASOS = list(itertools.product(Alvo, Estado, Acao, Papel, (AUTOR, OUTRO)))


@pytest.mark.parametrize(("alvo", "estado", "acao", "papel", "ator"), CASOS)
def test_todas_as_combinacoes(alvo, estado, acao, papel, ator):
    s = Situacao(
        alvo, estado, AUTOR, versao_atual=2, versao_aprovada=2, validade_fim=AGORA + timedelta(days=1)
    )
    alvo_esperado = esperado(alvo.value, estado.value, acao.value, papel.value, ator)
    try:
        resultado: str | int = aplicar(
            s, acao, ator, [papel.value], AGORA, justificativa="Ajustar o título."
        ).value
    except TransicaoNegada as recusa:
        resultado = recusa.status
        assert recusa.mensagem  # sempre com mensagem pronta para a tela
    assert resultado == alvo_esperado


def test_numero_de_casos_cobre_tudo():
    assert len(CASOS) == 2 * 6 * 6 * 4 * 2


def _aprovado(**kw) -> Situacao:
    base = dict(versao_atual=3, versao_aprovada=3, validade_fim=AGORA + timedelta(hours=6))
    base.update(kw)
    return Situacao(Alvo.COMUNICADO, Estado.APROVADO, AUTOR, **base)


def test_rn04_so_publica_a_versao_aprovada():
    with pytest.raises(TransicaoNegada) as e:
        aplicar(_aprovado(versao_atual=4), Acao.PUBLICAR, OUTRO, ["coordenacao"], AGORA)
    assert e.value.status == 409


def test_rn14_validade_obrigatoria_e_nao_vencida():
    with pytest.raises(TransicaoNegada, match="Defina até quando"):
        aplicar(_aprovado(validade_fim=None), Acao.PUBLICAR, OUTRO, ["coordenacao"], AGORA)
    with pytest.raises(TransicaoNegada, match="já terminou"):
        aplicar(_aprovado(validade_fim=AGORA), Acao.PUBLICAR, OUTRO, ["coordenacao"], AGORA)


def test_devolver_exige_justificativa():
    s = Situacao(Alvo.AVALIACAO, Estado.EM_REVISAO, AUTOR, versao_atual=1)
    with pytest.raises(TransicaoNegada) as e:
        aplicar(s, Acao.DEVOLVER, OUTRO, ["revisor"], AGORA, justificativa="   ")
    assert e.value.status == 422


def test_rn05_vale_ate_para_o_administrador():
    s = Situacao(Alvo.COMUNICADO, Estado.EM_REVISAO, AUTOR, versao_atual=1)
    with pytest.raises(TransicaoNegada, match="Outra pessoa precisa revisá-la"):
        aplicar(s, Acao.APROVAR, AUTOR, ["administrador"], AGORA)


def test_acoes_possiveis_para_a_interface():
    s = Situacao(Alvo.COMUNICADO, Estado.EM_REVISAO, AUTOR, versao_atual=1)
    assert Acao.APROVAR not in acoes_possiveis(s, AUTOR, ["revisor"], AGORA)
    assert set(acoes_possiveis(s, OUTRO, ["revisor"], AGORA)) == {Acao.EDITAR, Acao.APROVAR, Acao.DEVOLVER}
