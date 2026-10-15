from datetime import UTC, date, datetime

import pytest

from climasense.dominio.recorte import Recorte, RecorteInvalido, dia_no_recife, validar_territorio


@pytest.mark.parametrize("ok", ["recife", "ds-1", "ds-8", "bairro-boa-viagem", "bairro-afogados"])
def test_territorios_validos(ok):
    assert validar_territorio(ok) == ok


@pytest.mark.parametrize("ruim", ["ds-9", "ds-0", "Recife", "bairro-", "bairro-Boa Viagem", "olinda", ""])
def test_territorios_invalidos_tem_mensagem_para_a_tela(ruim):
    with pytest.raises(RecorteInvalido, match="não existe"):
        validar_territorio(ruim)


def test_periodo_invertido_e_recusado():
    with pytest.raises(RecorteInvalido, match="anterior ou igual"):
        Recorte("recife", date(2026, 10, 15), date(2026, 10, 1))


def test_intervalo_utc_respeita_o_fuso_do_recife():
    inicio, fim = Recorte("ds-4", date(2026, 10, 15), date(2026, 10, 15)).intervalo_utc()
    assert inicio == datetime(2026, 10, 15, 3, 0, tzinfo=UTC)
    assert fim == datetime(2026, 10, 16, 3, 0, tzinfo=UTC)


def test_troca_de_dia_utc_versus_recife():
    # 02h30 UTC do dia 16 ainda é dia 15 no Recife (UTC−3)
    assert dia_no_recife(datetime(2026, 10, 16, 2, 30, tzinfo=UTC)) == date(2026, 10, 15)


def test_granularidade():
    assert Recorte("recife", date(2026, 1, 1), date(2026, 1, 2)).granularidade == "municipio"
    assert Recorte("ds-5", date(2026, 1, 1), date(2026, 1, 2)).granularidade == "distrito"
    assert Recorte("bairro-afogados", date(2026, 1, 1), date(2026, 1, 2)).granularidade == "bairro"
