"""T6.2–T6.4 (domínio): lacunas viram null, o resumo cita as lacunas e a regra de cenário é honesta."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from climasense.dominio import cenario, series

SET = {date(2026, 9, d): 1.0 for d in range(1, 31)}


def test_dia_ausente_e_lacuna_e_nunca_zero():
    diarios = {**SET, date(2026, 9, 10): None}
    del diarios[date(2026, 9, 11)]
    pontos = series.agregar(diarios, date(2026, 9, 9), date(2026, 9, 12), "diaria")
    assert [p.valor for p in pontos] == [1.0, None, None, 1.0]
    assert series.dias_sem_dado(diarios, date(2026, 9, 1), date(2026, 9, 30)) == 2


def test_periodo_com_lacuna_nao_soma_so_os_dias_disponiveis():
    diarios = {**SET, date(2026, 9, 10): None}
    semanas = series.agregar(diarios, date(2026, 9, 7), date(2026, 9, 20), "semanal")
    assert [(p.inicio, p.valor, p.dias_com_dado) for p in semanas] == [
        (date(2026, 9, 7), None, 6),
        (date(2026, 9, 14), 7.0, 7),
    ]
    zero = series.agregar({date(2026, 9, 1): 0.0}, date(2026, 9, 1), date(2026, 9, 1), "mensal")
    assert zero[0].valor == 0.0  # zero medido continua zero (RN-02)


def test_resumo_compara_com_a_media_e_cita_lacunas():
    mensal = series.agregar(SET, date(2026, 9, 1), date(2026, 9, 30), "mensal")
    frase = series.resumo_em_frase(mensal, {9: (48.4, [2021, 2022, 2023, 2024, 2025])}, lacunas_dias=4)
    assert frase == (
        "Setembro de 2026 teve 38% menos chuva que a média de 2021 a 2025 (30,0 mm contra 48,4 mm). "
        "Faltam dados em 4 dias."
    )
    assert "Faltam" not in series.resumo_em_frase(mensal, {9: (48.4, [2021])}, 0)


# ------------------------------------------------------------------ cenário
AGORA = datetime(2026, 10, 15, 12, tzinfo=UTC)
HISTORICO = [0.0] * 300 + [5.0] * 50 + [20.0] * 10 + [40.0] * 5  # p95 ≈ 20, p99 ≈ 40


def _horas(valores):
    return [(AGORA + timedelta(hours=i), v) for i, v in enumerate(valores)]


def _insumos(chuva, mare=None, historico=HISTORICO, ocorrencias=None):
    return cenario.Insumos(
        chuva_prevista=_horas(chuva),
        mare_prevista=_horas(mare if mare is not None else [0.2] * 72),
        chuva_historica_diaria=historico,
        ocorrencias_historicas=ocorrencias,
    )


def test_sem_mare_e_dados_insuficientes_nunca_risco_baixo():
    e = cenario.estimar(_insumos([0.0] * 72, mare=[]), 72, AGORA)
    assert e.prioridade == "dados_insuficientes" and e.qualidade == "insuficiente"
    assert "maré" in e.limitacoes[0] and e.experimental


def test_historico_curto_e_dados_insuficientes():
    assert (
        cenario.estimar(_insumos([0.0] * 72, historico=[1.0] * 10), 72, AGORA).prioridade
        == "dados_insuficientes"
    )


def test_chuva_acima_do_p99_com_mare_alta_sobe_para_critico():
    chuva = [0.0] * 10 + [5.0] * 12 + [0.0] * 50  # 60 mm concentrados
    mare = [0.2] * 11 + [0.9] * 4 + [0.2] * 57
    e = cenario.estimar(_insumos(chuva, mare), 72, AGORA)
    assert e.prioridade == "critico"
    assert e.janela_atencao.inicio == AGORA + timedelta(hours=10)
    assert any(n == "Maré alta junto com a chuva" for n, _ in e.fatores)


def test_chuva_comum_nao_tem_indicacao_e_a_prioridade_nao_e_porcentagem():
    e = cenario.estimar(_insumos([0.1] * 72), 24, AGORA)
    assert e.prioridade == "sem_indicacao" and e.janela_atencao is None
    texto = " ".join(d for _, d in e.fatores) + " ".join(e.limitacoes)
    assert "%" not in e.prioridade and "chance" not in texto.lower()
    assert e.qualidade == "parcial"  # sem histórico de ocorrências integrado


def test_horizonte_invalido():
    with pytest.raises(ValueError):
        cenario.estimar(_insumos([0.0] * 72), 12, AGORA)
