"""População vulnerável: supressão do projeto e do IBGE, soma por distrito (RNF-03, RN-01, RN-02, RN-13)."""

from climasense.dominio import vulnerabilidade as v


def test_publicar_bairro_suprime_abaixo_do_minimo_mas_mantem_zero_medido():
    c = {
        "0-4": (3, False),
        "0-14": (0, False),
        "60+": (1200, False),
        "80+": (None, True),
        "total": (9000, False),
    }
    valores, marcas = v.publicar_bairro(c, 5)
    assert valores["criancas_0_4"] is None and marcas["criancas_0_4"] is True  # 3 < 5: do projeto
    assert valores["criancas_0_14"] == 0 and marcas["criancas_0_14"] is False  # zero medido
    assert valores["idosos_60_mais"] == 1200 and marcas["idosos_60_mais"] is False
    assert valores["idosos_80_mais"] is None and marcas["idosos_80_mais"] is True  # do IBGE
    assert valores["total"] == 9000


def test_bairro_sem_linhas_fica_nulo_e_nao_suprimido():
    valores, marcas = v.publicar_bairro(None, 5)
    assert set(valores.values()) == {None} and not any(marcas.values())


def test_soma_do_distrito_usa_valores_reais_e_fica_nula_se_faltar_um_bairro():
    a = {"60+": (3, False), "0-14": (10, False)}  # 3 é suprimido no bairro, mas entra no agregado do distrito
    b = {"60+": (100, False), "0-14": (20, False)}
    soma = v.somar_bairros([a, b])
    assert soma["idosos_60_mais"] == 103 and soma["criancas_0_14"] == 30
    assert v.somar_bairros([a, None])["idosos_60_mais"] is None
    assert v.somar_bairros([a, {"60+": (None, True)}])["idosos_60_mais"] is None
    assert v.somar_bairros([])["total"] is None


def test_somar_publicados():
    assert v.somar_publicados([1, None, 4]) == (5, True)
    assert v.somar_publicados([1, 2]) == (3, False)
    assert v.somar_publicados([None]) == (None, True)
    assert v.somar_publicados([]) == (None, False)


def test_texto_de_deficiencia_nomeia_o_motivo():
    assert v.FALTA_DEFICIENCIA.startswith("Dados insuficientes")
    assert "área de ponderação" in v.FALTA_DEFICIENCIA
