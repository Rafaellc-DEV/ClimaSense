from climasense.dominio.supressao import deve_suprimir, suprimir
from climasense.servicos.saude_agravos import _suprimir_bairros


def test_celulas_de_um_a_quatro_sao_suprimidas_e_zero_continua_zero():
    assert [suprimir(v, 5) for v in (0, 1, 4, 5, 6, None)] == [
        (0, False),
        (None, True),
        (None, True),
        (5, False),
        (6, False),
        (None, False),
    ]
    assert deve_suprimir(2, 3) and not deve_suprimir(3, 3)


def _b(nome, casos, notif=None):
    return {
        "bairro_id": nome,
        "bairro_nome": nome,
        "casos": casos,
        "notificados": notif if notif is not None else casos,
    }


def test_ordem_nao_vaza_o_valor_suprimido():
    itens, houve = _suprimir_bairros([_b("A", 0), _b("B", 3), _b("C", 12), _b("D", 1), _b("E", 7)], 5)
    assert houve is True
    assert [i["bairro_id"] for i in itens] == [
        "C",
        "E",
        "B",
        "D",
        "A",
    ]  # >=5 por casos, suprimidos por nome, zeros
    assert [i["casos"] for i in itens] == [12, 7, None, None, 0]
    assert [i["suprimido"] for i in itens] == [False, False, True, True, False]


def test_sem_celula_pequena_nada_e_suprimido():
    itens, houve = _suprimir_bairros([_b("A", 0), _b("B", 9)], 5)
    assert houve is False and all(not i["suprimido"] for i in itens)
