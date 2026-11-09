"""Ordenação da prioridade por vulnerabilidade (RF-06): posição, desempate e empate dividido (RN-06: sem %)."""

from climasense.servicos.prioridade_vulnerabilidade import CRITERIOS, _posicoes


def _i(nome: str, alag: int, desl: int) -> dict:
    return {"nome": nome, "ocorrencias_alagamento": alag, "ocorrencias_deslizamento": desl}


def test_ordena_pelo_total_desempata_por_alagamento_e_posicoes_sao_unicas():
    itens = _posicoes([_i("D", 1, 0), _i("B", 0, 5), _i("A", 5, 0), _i("C", 5, 0), _i("Z", 0, 0)])
    assert [(i["nome"], i["posicao"]) for i in itens] == [("A", 1), ("C", 2), ("B", 3), ("D", 4), ("Z", 5)]


def test_criterio_nomeia_so_o_que_entra_na_ordem():
    assert CRITERIOS == ("atendimentos de alagamento e deslizamento",)


def test_nomes_iguais_empatados_tem_posicoes_distintas_e_ordem_estavel_pelo_id():
    # dois bairros "Cohab" com a mesma contagem: nunca duas posições 1; o id decide a ordem, sempre igual
    cohab = [
        {**_i("Cohab", 3, 0), "territorio_id": "bairro-cohab-b"},
        {**_i("Cohab", 3, 0), "territorio_id": "bairro-cohab-a"},
        {**_i("Outro", 1, 0), "territorio_id": "bairro-outro"},
    ]
    saida = _posicoes(list(cohab))
    assert [(i["territorio_id"], i["posicao"]) for i in saida] == [
        ("bairro-cohab-a", 1),
        ("bairro-cohab-b", 2),
        ("bairro-outro", 3),
    ]
    assert [i["territorio_id"] for i in _posicoes(list(reversed(cohab)))] == [
        i["territorio_id"] for i in saida
    ]
    assert [i["posicao"] for i in saida] == list(range(1, len(saida) + 1))
