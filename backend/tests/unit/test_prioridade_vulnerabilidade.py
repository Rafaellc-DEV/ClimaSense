"""Ordenação da prioridade por vulnerabilidade (RF-06): posição, desempate e empate dividido (RN-06: sem %)."""

from climasense.servicos.prioridade_vulnerabilidade import CRITERIOS, _posicoes


def _i(nome: str, alag: int, desl: int) -> dict:
    return {"nome": nome, "ocorrencias_alagamento": alag, "ocorrencias_deslizamento": desl}


def test_ordena_pelo_total_desempata_por_alagamento_e_empatados_dividem_a_posicao():
    itens = _posicoes([_i("D", 1, 0), _i("B", 0, 5), _i("A", 5, 0), _i("C", 5, 0), _i("Z", 0, 0)])
    assert [(i["nome"], i["posicao"]) for i in itens] == [("A", 1), ("C", 1), ("B", 3), ("D", 4), ("Z", 5)]


def test_criterio_nomeia_so_o_que_entra_na_ordem():
    assert CRITERIOS == ("atendimentos de alagamento e deslizamento",)
