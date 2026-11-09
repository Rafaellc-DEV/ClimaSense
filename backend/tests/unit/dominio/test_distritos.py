import pytest

from climasense.dominio.distritos import nome_distrito


@pytest.mark.parametrize(
    ("entrada", "saida"),
    [
        ("Distrito Sanitário I", "Distrito 1"),
        ("Distrito Sanitário V", "Distrito 5"),
        ("Distrito Sanitário VII", "Distrito 7"),
        ("Distrito Sanitário VIII", "Distrito 8"),  # VIII antes de VII
        ("Distrito VIII", "Distrito 8"),
        ("Distrito VI", "Distrito 6"),
        ("DS IV", "Distrito 4"),
        ("ds iii", "Distrito 3"),
        ("Distrito Sanitario II", "Distrito 2"),  # sem acento
        ("Distrito 5", "Distrito 5"),  # já convertido: idempotente
        ("Sem distrito aqui", "Sem distrito aqui"),
        ("Boa Viagem", "Boa Viagem"),
        (
            "Distrito Sanitário VIII e Distrito Sanitário II em alerta (DS V)",
            "Distrito 8 e Distrito 2 em alerta (Distrito 5)",
        ),  # fmt: skip
    ],
)
def test_nome_distrito(entrada, saida):
    assert nome_distrito(entrada) == saida


def test_nome_distrito_none_e_idempotente():
    assert nome_distrito(None) is None
    assert nome_distrito(nome_distrito("DS VII")) == "Distrito 7"


def test_nao_mexe_em_palavra_que_so_comeca_igual():
    assert nome_distrito("DSV novo") == "DSV novo"
    assert nome_distrito("Distritos VII") == "Distritos VII"
