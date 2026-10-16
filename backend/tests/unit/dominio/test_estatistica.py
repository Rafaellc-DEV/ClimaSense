"""T6.1 — estatística das Atividades 3 e 4, sem o `'...' → 0` (RN-02).

A série PNAD (desocupação em Pernambuco) entra só como fixture: os valores esperados são os do
`Atividade4/relatorio.md`, calculados lá com pandas.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from climasense.dominio import estatistica as e

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "pnad_pe_desocupacao.json"


@pytest.fixture(scope="module")
def pnad() -> dict[str, list[float]]:
    dados = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return {c: [d[c] for d in dados] for c in ("total", "mulheres", "homens")}


@pytest.mark.parametrize(
    ("serie", "variancia", "desvio", "assimetria", "curtose"),
    [
        ("total", 11.1491, 3.3390, 0.2771, -1.2084),
        ("mulheres", 11.7598, 3.4293, 0.0706, -1.2702),
        ("homens", 11.3397, 3.3674, 0.4724, -0.9643),
    ],
)
def test_reproduz_o_relatorio_da_atividade_4(pnad, serie, variancia, desvio, assimetria, curtose):
    x = pnad[serie]
    assert e.variancia(x) == pytest.approx(variancia, abs=1e-4)
    assert e.desvio_padrao(x) == pytest.approx(desvio, abs=1e-4)
    assert e.assimetria(x) == pytest.approx(assimetria, abs=1e-4)
    assert e.curtose(x) == pytest.approx(curtose, abs=1e-4)


def test_tendencia_central_e_amplitude(pnad):
    x = pnad["total"]
    assert e.media(x) == pytest.approx(12.35, abs=0.01)
    assert e.mediana(x) == pytest.approx(11.80, abs=1e-9)
    assert e.moda(x) == [9.2, 14.2]
    assert e.amplitude(x) == pytest.approx((7.4, 19.0, 11.6))
    assert e.moda(pnad["homens"])[:2] == [
        6.8,
        7.4,
    ]  # o relatório cita só as duas primeiras (“moda principal”)


def test_nulo_e_ignorado_e_nunca_vira_zero():
    assert e.media([2.0, None, 4.0]) == 3.0
    assert e.validos([0.0, None, 1.5]) == [0.0, 1.5]  # zero medido continua zero
    resumo = e.descrever([None, None])
    assert resumo.n == 0 and resumo.media is None and resumo.variancia is None


def test_classificar_curtose_como_na_atividade_4():
    assert e.classificar_curtose(-1.2084).startswith("Platicúrtica")
    assert e.classificar_curtose(0.1).startswith("Mesocúrtica")
    assert e.classificar_curtose(2.5).startswith("Leptocúrtica")


def test_amostras_pequenas_nao_inventam_medidas():
    r = e.descrever([5.0, 7.0])
    assert r.n == 2 and r.media == 6.0
    assert r.assimetria is None and r.curtose is None  # exigem 3 e 4 observações
    assert e.descrever([1.0]).variancia is None
