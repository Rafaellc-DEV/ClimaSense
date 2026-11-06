from datetime import UTC, datetime, timedelta

import pytest

from climasense.etl import frescor
from climasense.etl.conectores import IMPLEMENTADOS

AGORA = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)


def test_todo_conector_implementado_tem_limite():
    assert [i for i in IMPLEMENTADOS if frescor.limite_frescor_h(i) is None] == []


def test_limites_documentados():
    assert frescor.limite_frescor_h("open-meteo-previsao") == 6
    assert frescor.limite_frescor_h("apac-chuva") == 1
    assert frescor.limite_frescor_h("infodengue") == 192
    assert frescor.limite_frescor_h("sinan-leptospirose") == 360
    assert frescor.limite_frescor_h("recife-arboviroses") == 9600


def test_territorio_estatico_e_fonte_desconhecida_sem_limite():
    assert frescor.limite_frescor_h("territorio-oficial") is None
    assert frescor.limite_frescor_h("nao-existe") is None
    assert frescor.esta_desatualizado("territorio-oficial", AGORA - timedelta(days=900), AGORA) is None


def test_sem_dado_nunca_e_em_dia():
    assert frescor.esta_desatualizado("apac-chuva", None, AGORA) is None


@pytest.mark.parametrize(
    ("idade_h", "esperado"),
    [(0.5, False), (1, False), (1.01, True), (30, True)],
)
def test_apac_na_fronteira(idade_h, esperado):
    assert frescor.esta_desatualizado("apac-chuva", AGORA - timedelta(hours=idade_h), AGORA) is esperado


def test_fusos_misturados_falham_alto():
    with pytest.raises(ValueError, match="fuso"):
        frescor.esta_desatualizado("apac-chuva", datetime(2026, 11, 6, 11), AGORA)
