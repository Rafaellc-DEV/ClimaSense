"""Classe de impacto das arboviroses por distrito: terços entre os distritos com casos (RN-06, RN-11)."""

from climasense.servicos.arboviroses_cenario import AVISO, MOTIVO_ZIKA, _classes


def test_tercos_entre_os_distritos_com_casos_e_zero_medido_e_baixa():
    c = _classes({"a": 30, "b": 10, "c": 3, "d": 0, "e": 0})
    assert c == {"a": "alta", "b": "media", "c": "baixa", "d": "baixa", "e": "baixa"}


def test_empate_no_valor_fica_na_mesma_classe_e_sem_dado_nao_vira_classe():
    assert set(_classes({"a": 7, "b": 7, "c": 7}).values()) == {"alta"}
    assert _classes({"a": 0, "b": 0}) == {"a": "baixa", "b": "baixa"}
    assert _classes({}) == {}  # sem a fonte: nenhuma classe (RN-01)


def test_textos_deixam_claro_que_e_contexto_e_que_zika_nao_tem_dado():
    assert "CONTEXTO" in AVISO and "não previsão causal da chuva" in AVISO and "%" not in AVISO
    assert MOTIVO_ZIKA.startswith("Dados insuficientes") and "infodengue" in MOTIVO_ZIKA
