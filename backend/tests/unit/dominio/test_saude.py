"""Semana epidemiológica, janela de leptospirose e variação de 4 semanas (regras puras)."""

from datetime import date

import pytest

from climasense.dominio import janela_leptospirose as janela
from climasense.dominio import semana_epi
from climasense.servicos.saude_agravos import variacao_4s_pct


@pytest.mark.parametrize(
    ("dia", "esperado"),
    [
        (date(2026, 10, 25), (2026, 43)),  # data_iniSE real do InfoDengue (SE 202643)
        (date(2026, 1, 3), (2025, 53)),  # 2025 teve 53 semanas: 03/01/2026 ainda é da SE 53
        (date(2026, 1, 4), (2026, 1)),
        (date(2015, 1, 4), (2015, 1)),
        (date(2014, 12, 31), (2014, 53)),
    ],
)
def test_semana_epidemiologica_do_ministerio(dia, esperado):
    assert semana_epi.semana_de(dia) == esperado
    assert semana_epi.inicio_semana(*esperado) <= dia


def test_codigo_da_semana():
    assert semana_epi.de_codigo("202643") == (2026, 43)
    assert semana_epi.de_codigo(202019.0) == (2020, 19)
    assert semana_epi.de_codigo("202653") is None  # 2026 só tem 52 semanas
    assert semana_epi.de_codigo("") is None and semana_epi.de_codigo("2026") is None


def _g(dia, origem="estagio", t="recife", nome="Recife", desc="estágio Crítico declarado"):
    return janela.Gatilho(dia, origem, t, nome, desc)


def test_janela_de_30_dias_a_partir_do_gatilho():
    j = janela.calcular([_g(date(2026, 11, 5))], date(2026, 11, 13))
    assert j["ativa"] and (j["inicio"], j["fim"]) == (date(2026, 11, 5), date(2026, 12, 5))
    assert j["dia_da_janela"] == 9 and j["atencao_maior"]  # 5º a 14º dia: incubação média
    assert j["territorios"] == [{"id": "recife", "nome": "Recife"}]
    assert j["motivo"] == "estágio Crítico declarado em 05/11 (Recife)"


def test_gatilhos_encadeados_estendem_a_janela_e_somam_territorios():
    gatilhos = [
        _g(date(2026, 10, 1), "chuva", "ds-4", "Distrito IV", "72 mm em 24 h"),
        _g(date(2026, 10, 20), "ocorrencia", "bairro-ibura", "Ibura", "2 atendimento(s) de alagamento"),
        _g(date(2026, 8, 1)),  # fora dos 60 dias
    ]
    j = janela.calcular(gatilhos, date(2026, 11, 5))
    assert j["ativa"] and j["inicio"] == date(2026, 10, 1) and j["fim"] == date(2026, 11, 19)
    assert [t["id"] for t in j["territorios"]] == ["ds-4", "bairro-ibura"]
    assert j["origens"] == ["chuva", "ocorrencia"]


def test_janela_encerrada_e_sem_gatilho():
    j = janela.calcular([_g(date(2026, 9, 20))], date(2026, 11, 5))
    assert j is not None and not j["ativa"] and j["fim"] == date(2026, 10, 20) and j["dia_da_janela"] is None
    assert janela.calcular([], date(2026, 11, 5)) is None
    assert janela.calcular([_g(date(2026, 11, 6))], date(2026, 11, 5)) is None  # gatilho no futuro não vale


def _s(casos, est=None, incompleta=False):
    return {"casos": casos, "casos_estimados": est, "incompleta": incompleta}


def test_variacao_usa_a_estimativa_ou_pula_as_semanas_incompletas():
    com_est = [_s(10, 20)] * 4 + [_s(10, 10)] * 4
    assert variacao_4s_pct(com_est, True) == 100.0
    sinan = [_s(1, incompleta=True)] * 6 + [_s(6)] * 4 + [_s(4)] * 4
    assert variacao_4s_pct(sinan, False) == 50.0  # as 6 incompletas não entram
    assert variacao_4s_pct([_s(3)] * 7, False) is None  # menos de 8 semanas
    assert variacao_4s_pct([_s(3)] * 4 + [_s(0)] * 4, False) is None  # base zero
