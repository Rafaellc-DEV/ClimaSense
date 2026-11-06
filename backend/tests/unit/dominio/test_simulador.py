"""Regras do simulador (PRD §8, RF-23 a RF-25): classes ordinais, sem_dados, sensibilidade e motivos."""

import pytest

from climasense.dominio import estagio as est
from climasense.dominio import simulador as sim

PAR = est.Parametros()


def prem(chuva=0.0, acum=0.0, mare=0.0, dur=24.0, hor=24, **kw):
    return sim.Premissas(chuva, dur, acum, mare, hor, **kw)


def hist(alag=0, desl=0, desde=2014):
    return sim.Historico(alag, desl, desde)


# ------------------------------------------------------------------ alagamento
@pytest.mark.parametrize(
    ("chuva", "esperada"),
    [(10, "observacao"), (30, "atencao"), (55, "alerta"), (95, "critico")],
)
def test_cada_classe_de_alagamento_pelos_gatilhos_de_24h(chuva, esperada):
    classe, _, _ = sim.classificar_alagamento(prem(chuva=chuva), PAR, hist())
    assert classe == esperada


def test_limiares_sao_os_dos_estagios():
    p = est.Parametros(chuva_prev_24h_atencao_mm=40.0)
    assert sim.classificar_alagamento(prem(chuva=30), p, hist())[0] == "observacao"


def test_chuva_longa_se_espalha_pela_duracao():
    # 100 mm em 48 h: 50 mm nas 24 h mais chuvosas (alerta) e 100 mm em 72 h (alerta)
    classe, motivos, _ = sim.classificar_alagamento(prem(chuva=100, dur=48, hor=48), PAR, hist())
    assert classe == "alerta"
    assert sim.chuva_na_janela(prem(chuva=100, dur=48), 24) == 50.0
    assert "alerta" in motivos[0]


def test_chuva_acumulada_sozinha_dispara_o_gatilho_de_72h():
    assert sim.classificar_alagamento(prem(acum=110), PAR, hist())[0] == "alerta"


def test_mare_alta_sobe_um_nivel_so_com_chuva_acima_do_limiar():
    assert sim.classificar_alagamento(prem(chuva=55, mare=2.3), PAR, hist())[0] == "critico"
    classe, motivos, _ = sim.classificar_alagamento(prem(chuva=10, mare=2.3), PAR, hist())
    assert classe == "observacao"
    assert not any("maré" in m for m in motivos)
    assert sim.classificar_alagamento(prem(chuva=55, mare=0.2), PAR, hist())[0] == "alerta"


def test_motivo_de_mare_cita_o_nivel():
    _, motivos, _ = sim.classificar_alagamento(prem(chuva=55, mare=2.3), PAR, hist())
    assert "maré de 2,3 m junto do pico: sobe um nível" in motivos


def test_historico_do_bairro_sobe_um_nivel_e_aparece_nos_motivos():
    classe, motivos, forte = sim.classificar_alagamento(prem(chuva=30), PAR, hist(alag=14))
    assert classe == "alerta" and forte
    assert "14 atendimentos de alagamento desde 2014" in motivos


def test_motivo_do_gatilho_tem_valor_e_limiar():
    _, motivos, _ = sim.classificar_alagamento(prem(chuva=72), PAR, hist())
    assert motivos[0] == "72 mm previstos em 24 h, acima do limiar de alerta (50 mm)"


def test_sem_carga_de_ocorrencias_alagamento_e_sem_dados_nunca_baixo():
    classe, motivos, _ = sim.classificar_alagamento(prem(chuva=0), PAR, sim.Historico(None, None))
    assert classe == "sem_dados"
    assert sim.MOTIVO_SEM_ALAGAMENTO in motivos


def test_zero_medido_de_alagamento_e_classificado_nao_e_sem_dados():
    assert sim.classificar_alagamento(prem(chuva=0), PAR, hist(alag=0))[0] == "observacao"


# ------------------------------------------------------------------ sensibilidade (prefere falso positivo)
def test_bairro_com_historico_sobe_para_atencao_perto_do_limiar():
    classe, motivos, _ = sim.classificar_alagamento(prem(chuva=21), PAR, hist(alag=4))
    assert classe == "atencao"
    assert any("perto do limiar de atenção" in m for m in motivos)


def test_perto_do_limiar_sem_historico_continua_observacao():
    assert sim.classificar_alagamento(prem(chuva=21), PAR, hist(alag=0))[0] == "observacao"
    assert sim.classificar_alagamento(prem(chuva=15), PAR, hist(alag=4))[0] == "observacao"


# ------------------------------------------------------------------ deslizamento
def test_deslizamento_sem_historico_do_bairro_e_sem_dados_mesmo_com_chuva_forte():
    classe, motivos = sim.classificar_deslizamento(prem(chuva=200), PAR, hist(desl=0))
    assert classe == "sem_dados"
    assert motivos == [sim.MOTIVO_SEM_DESLIZAMENTO]
    assert sim.classificar_deslizamento(prem(chuva=200), PAR, sim.Historico(None, None))[0] == "sem_dados"


@pytest.mark.parametrize(
    ("chuva", "esperada"), [(10, "observacao"), (30, "atencao"), (55, "alerta"), (95, "critico")]
)
def test_cada_classe_de_deslizamento_com_historico(chuva, esperada):
    assert sim.classificar_deslizamento(prem(chuva=chuva), PAR, hist(desl=1))[0] == esperada


def test_mare_nao_interfere_em_deslizamento():
    assert sim.classificar_deslizamento(prem(chuva=30, mare=3.0), PAR, hist(desl=1))[0] == "atencao"


def test_solo_saturado_sobe_um_nivel():
    classe, motivos = sim.classificar_deslizamento(prem(chuva=30, acum=70), PAR, hist(desl=1))
    assert classe == "alerta"
    assert any("solo saturado" in m for m in motivos)
    # só saturação, sem chuva prevista: não sobe
    assert sim.classificar_deslizamento(prem(chuva=0, acum=70), PAR, hist(desl=1))[0] == "atencao"


def test_historico_de_deslizamento_forte_sobe_um_nivel():
    classe, motivos = sim.classificar_deslizamento(prem(chuva=55), PAR, hist(desl=3))
    assert classe == "critico"
    assert "3 atendimentos de deslizamento desde 2014" in motivos


# ------------------------------------------------------------------ estágio, confiança, motivos
@pytest.mark.parametrize(
    ("a", "d", "esperado"),
    [
        ("observacao", "sem_dados", "sem_dados"),
        ("atencao", "sem_dados", "atencao"),
        ("alerta", "atencao", "alerta"),
        ("observacao", "observacao", "observacao"),
        ("sem_dados", "sem_dados", "sem_dados"),
    ],
)
def test_estagio_sugerido_nunca_afirma_observacao_com_perigo_desconhecido(a, d, esperado):
    assert sim.estagio_sugerido(a, d) == esperado


def test_confianca_nunca_e_alta_sem_validacao():
    assert sim.confianca("critico", "critico") == "media"
    assert sim.confianca("critico", "sem_dados") == "baixa"
    assert sim.confianca("sem_dados", "sem_dados") == "insuficiente"


def test_bairro_motivos_curtos_e_sem_dados_tem_vaga_garantida():
    r = sim.classificar_bairro(prem(chuva=72, acum=80, mare=2.3), PAR, hist(alag=14, desl=0))
    assert 1 <= len(r.motivos) <= sim.MAX_MOTIVOS
    assert sim.MOTIVO_SEM_DESLIZAMENTO in r.motivos
    assert r.classe_deslizamento == "sem_dados" and r.confianca == "baixa"
    assert r.estagio_sugerido == "critico"
    assert all(len(m) < 110 for m in r.motivos)


def test_classes_so_no_vocabulario_ordinal():
    for chuva in (0, 30, 60, 120):
        r = sim.classificar_bairro(prem(chuva=chuva), PAR, hist(alag=1, desl=1))
        assert r.classe_alagamento in ("sem_dados", *sim.ESCADA)
        assert "%" not in " ".join(r.motivos)


def test_distrito_e_o_pior_bairro_e_sem_dados_nao_puxa_para_baixo():
    a = sim.classificar_bairro(prem(chuva=55), PAR, hist(alag=0, desl=1))
    b = sim.classificar_bairro(prem(chuva=55), PAR, sim.Historico(None, None))
    d = sim.agregar_distrito([("Boa Vista", a), ("Casa Amarela", b)])
    assert d.classe_alagamento == "alerta"
    assert d.confianca == "baixa"
    assert any("sem dados suficientes" in m for m in d.motivos)
    assert len(d.motivos) <= sim.MAX_MOTIVOS


def test_distrito_sem_nenhum_dado_e_sem_dados():
    b = sim.classificar_bairro(prem(chuva=55), PAR, sim.Historico(None, None))
    d = sim.agregar_distrito([("A", b), ("B", b)])
    assert (d.classe_alagamento, d.classe_deslizamento, d.estagio_sugerido) == ("sem_dados",) * 3
    assert d.confianca == "insuficiente"
    assert sim.agregar_distrito([]).estagio_sugerido == "sem_dados"


# ------------------------------------------------------------------ abrigos e impacto
def test_pressao_dos_abrigos_so_repete_o_informado():
    assert sim.pressao_abrigos(prem()) is None
    assert (
        sim.pressao_abrigos(prem(abrigos_abertos=3, capacidade_abrigos=450))
        == "capacidade informada de 450 pessoas em 3 abrigos"
    )
    assert "1 abrigo" in sim.pressao_abrigos(prem(abrigos_abertos=1, capacidade_abrigos=80))
    assert "não informada" in sim.pressao_abrigos(prem(abrigos_abertos=2))


def test_impacto_nulo_sem_fonte_e_estrutura_pronta_para_somar():
    assert sim.impacto_pessoas("alerta", None) is None
    v = sim.Vulneraveis(idosos=1200, criancas=800, equipamentos_saude=4)
    assert sim.impacto_pessoas("observacao", v) is None
    assert sim.impacto_pessoas("sem_dados", v) is None
    i = sim.impacto_pessoas("alerta", v)
    assert i["total_pessoas"] == 2000 and i["equipamentos_saude"] == 4
    assert sim.impacto_pessoas("alerta", sim.Vulneraveis())["total_pessoas"] is None
