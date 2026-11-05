"""Ponto-em-polígono com a base oficial local (malha de bairros e distritos sanitários do Recife)."""

from climasense.territorio.carga import geo_local
from climasense.territorio.geometria import Localizador, carregar_malha_bairros, contorno_recife


def test_estacao_cai_no_bairro_oficial_e_no_distrito_do_bairro():
    malha = carregar_malha_bairros(baixar=False)
    assert malha is not None and len(malha["features"]) == 94
    loc = Localizador(geo_local(), malha)
    assert loc.localizar(-34.8835, -8.0848) == ("bairro-pina", "ds-6")  # [CEMADEN] Pina
    assert loc.localizar(-34.9464, -8.1214) == ("bairro-cohab", "ds-8")  # "COHAB" (nome oficial com sufixo)
    assert loc.localizar(-35.2, -8.3) == (None, None)  # fora do Recife
    assert loc.localizar(None, -8.0) == (None, None)


def test_sem_malha_de_bairros_fica_no_distrito(tmp_path):
    assert carregar_malha_bairros(pasta=tmp_path, baixar=False) is None
    loc = Localizador(geo_local(), None)
    assert not loc.tem_bairros and loc.localizar(-34.8835, -8.0848) == (None, "ds-6")


def test_contorno_do_recife_contem_o_marco_zero():
    from shapely.geometry import Point

    assert contorno_recife(geo_local()).covers(Point(-34.8711, -8.0631))
