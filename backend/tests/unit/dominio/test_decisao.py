"""Apoio à decisão (domínio): situação agora e ordenação de prioridades. Falta de dado nunca vira zero."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from climasense.dominio import prioridades as p
from climasense.dominio import situacao as s

AGORA = datetime(2026, 10, 15, 20, 30, tzinfo=UTC)
FIM = AGORA.replace(minute=0)


def _horas(n, valor=1.0, pular=()):
    return {FIM - timedelta(hours=i): (None if i in pular else valor) for i in range(1, n + 1)}


def test_acumulado_soma_so_com_todas_as_horas():
    j = s.acumulado_recente(_horas(24), AGORA, 24)
    assert (j.acumulado_mm, j.horas_com_dado, j.cobertura_pct) == (24.0, 24, 100.0)


def test_hora_faltando_nao_vira_zero_nem_total_parcial():
    j = s.acumulado_recente(_horas(24, pular={3}), AGORA, 24)
    assert j.acumulado_mm is None
    assert j.horas_com_dado == 23


def test_sem_nenhum_dado_e_insuficiente():
    j = s.acumulado_recente({}, AGORA, 72)
    assert (j.acumulado_mm, j.horas_com_dado, j.cobertura_pct) == (None, 0, 0.0)


def test_chuva_zero_medida_continua_zero():
    assert s.acumulado_recente(_horas(24, 0.0), AGORA, 24).acumulado_mm == 0.0


@pytest.mark.parametrize(
    ("mm", "trecho"),
    [(40.0, "dobro"), (15.0, "Acima"), (10.0, "Perto"), (2.0, "Abaixo")],
)
def test_comparacao_com_a_media_do_mes(mm, trecho):
    # média de 310 mm em outubro (31 dias) = 10 mm/dia
    c = s.comparar_com_referencia(mm, 310.0, 2026, 10, 24)
    assert c is not None and trecho in c.texto and c.referencia_mm == 10.0


def test_comparacao_sem_dado_ou_sem_referencia_e_none():
    assert s.comparar_com_referencia(None, 310.0, 2026, 10, 24) is None
    assert s.comparar_com_referencia(5.0, None, 2026, 10, 24) is None
    assert s.comparar_com_referencia(5.0, 0.0, 2026, 10, 24) is None


def test_pico_previsto_ignora_nulos_e_fora_do_horizonte():
    chuva = [(FIM + timedelta(hours=h), v) for h, v in [(1, 2.0), (2, None), (3, 9.5), (80, 50.0)]]
    assert s.pico_previsto(chuva, FIM) == (FIM + timedelta(hours=3), 9.5)
    assert s.pico_previsto([(FIM, None)], FIM) is None


def _c(i, estimador, equipe=None, intens=0.0, oc=None):
    return p.Candidato(i, estimador, equipe, intens, oc)


def test_ordem_nivel_depois_insuficiente_depois_sem_indicacao():
    cs = [
        _c("a", "sem_indicacao"),
        _c("b", "dados_insuficientes"),
        _c("c", "atencao"),
        _c("d", "critico"),
        _c("e", "alerta"),
    ]
    assert [c.territorio_id for c in p.ordenar(cs)] == ["d", "e", "c", "b", "a"]


def test_desempate_por_intensidade_e_depois_ocorrencias():
    cs = [_c("a", "alerta", intens=1.1), _c("b", "alerta", intens=1.4), _c("c", "alerta", intens=1.1, oc=7)]
    assert [c.territorio_id for c in p.ordenar(cs)] == ["b", "c", "a"]


def test_sinal_da_equipe_so_sobe_nunca_desce():
    assert p.nivel_efetivo(_c("a", "atencao", "critico")) == "critico"
    assert p.nivel_efetivo(_c("a", "critico", "atencao")) == "critico"
    assert p.nivel_efetivo(_c("a", "dados_insuficientes", "alerta")) == "alerta"
    assert p.nivel_efetivo(_c("a", "dados_insuficientes", "sem_indicacao")) == "dados_insuficientes"


def test_confianca_nunca_e_alta_e_cada_fragilidade_rebaixa():
    assert p.confianca("completa", 4, 0) == "media"
    assert p.confianca("parcial", 4, 0) == "baixa"
    assert p.confianca("completa", 1, 0) == "baixa"
    assert p.confianca("completa", 4, 1) == "baixa"
    assert p.confianca("insuficiente", 4, 0) == "insuficiente"


def test_motivos_por_peso():
    c = _c("a", "alerta")
    c.motivos = [p.Motivo("x", "", "qualidade", 20), p.Motivo("y", "", "estimador", 90)]
    assert [m.fator for m in p.motivos_ordenados(c)] == ["y", "x"]
