"""Ponto-em-polígono e cobertura das áreas de risco (RF-04, RN-01), sem banco."""

from climasense.servicos.vulnerabilidade import cobertura_risco, em_area_de_risco

QUADRADO = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}
LACO = {"type": "Polygon", "coordinates": [[[2, 2], [3, 3], [3, 2], [2, 3], [2, 2]]]}  # autointersecção


def _a(g, **kw):
    return {"geometria": g, "regional": None, "bairro_id": None, **kw}


def test_ponto_em_poligono_conta_dentro_e_ignora_fora():
    areas = [_a(QUADRADO)]
    assert em_area_de_risco([(0.5, 0.5), (5, 5), (0.9, 0.1)], areas) == 2
    assert em_area_de_risco([(5, 5)], areas) == 0
    assert em_area_de_risco([], areas) == 0 and em_area_de_risco([(0.5, 0.5)], []) == 0


def test_ponto_em_duas_areas_conta_uma_vez_e_geometria_invalida_nao_quebra():
    assert em_area_de_risco([(0.5, 0.5)], [_a(QUADRADO), _a(QUADRADO)]) == 1
    assert em_area_de_risco([(2.2, 2.5)], [_a(LACO)]) in (0, 1)


def test_cobertura_parcial_e_texto():
    areas = [
        _a(QUADRADO, regional="Regional 2", bairro_id="b1"),
        _a(QUADRADO, regional="Regional 2", bairro_id="b1"),
    ]
    cob = cobertura_risco(areas)
    assert cob["regionais_com_dado"] == ["Regional 2"] and cob["bairros_com_dado"] == 1
    assert cob["parcial"] is True and cob["total_bairros"] == 94
    completa = cobertura_risco([_a(QUADRADO, bairro_id=f"b{i}") for i in range(94)])
    assert completa["parcial"] is False and "todos os bairros" in completa["texto"]
