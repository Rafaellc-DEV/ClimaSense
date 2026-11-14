"""Testes determinísticos do experimento: sem rede, credenciais ou alterações remotas."""

from __future__ import annotations

import pandas as pd
import pytest

from climasense.ml.alagamento.base import ATRIBUTOS
from climasense.ml.alagamento.comparar_chuva_intensa import (
    NOVAS_FEATURES,
    picos_por_distrito_dia,
    preparar_mesma_amostra,
)


def _horas(inicio, fim, mm=0):
    t = pd.date_range(inicio, fim, freq="h")
    return pd.DataFrame({"territorio_id": "ds-1", "hora": t, "mm": float(mm)})


def test_picos_moveis_atravessam_meia_noite_sem_usar_horas_futuras():
    h = _horas("2023-02-09 19:00", "2023-02-10 23:00")
    h.loc[h.hora == pd.Timestamp("2023-02-09 23:00"), "mm"] = 7
    h.loc[h.hora == pd.Timestamp("2023-02-10 00:00"), "mm"] = 5
    h.loc[h.hora == pd.Timestamp("2023-02-10 01:00"), "mm"] = 8
    p = picos_por_distrito_dia(h).set_index("data").loc[pd.Timestamp("2023-02-10")]
    assert p.chuva_pico_1h == 8
    assert p.chuva_pico_3h == 20
    assert p.chuva_pico_6h == 20


def test_ausencia_de_uma_hora_invalida_o_dia_sem_zero_artificial():
    h = _horas("2023-02-09 19:00", "2023-02-10 23:00", mm=1)
    h = h[h.hora != pd.Timestamp("2023-02-10 12:00")]
    p = picos_por_distrito_dia(h).set_index("data").loc[pd.Timestamp("2023-02-10")]
    assert p[list(NOVAS_FEATURES)].isna().all()


def test_precisa_das_cinco_horas_anteriores():
    h = _horas("2023-02-10 00:00", "2023-02-10 23:00", mm=2)
    p = picos_por_distrito_dia(h).set_index("data").loc[pd.Timestamp("2023-02-10")]
    assert p[list(NOVAS_FEATURES)].isna().all()


def test_mm_negativo_nao_pode_ser_interpretado_como_seco():
    h = _horas("2023-02-09 19:00", "2023-02-10 23:00", mm=1)
    h.loc[h.hora == pd.Timestamp("2023-02-10 02:00"), "mm"] = -99
    p = picos_por_distrito_dia(h).set_index("data").loc[pd.Timestamp("2023-02-10")]
    assert p[list(NOVAS_FEATURES)].isna().all()


def test_cruzamento_mantem_mesma_amostra_e_ha_distritos_sem_chuva():
    dia = pd.Timestamp("2023-02-10")
    base = pd.DataFrame(
        {
            "territorio_id": ["bairro-a", "bairro-b", "bairro-c"],
            "distrito_id": ["ds-1", "ds-1", "ds-2"],
            "data": [dia] * 3,
            "alagou": [1, 0, 0],
            **{c: [1.0, 1.0, 1.0] for c in ATRIBUTOS},
        }
    )
    base.attrs["janela_rotulo_dias"] = 3
    picos = picos_por_distrito_dia(_horas("2023-02-09 19:00", "2023-02-10 23:00"))
    b, q = preparar_mesma_amostra(base, picos)
    assert list(b.territorio_id) == ["bairro-a", "bairro-b"]
    assert q["linhas_removidas_por_picos_ausentes"] == 1
    assert b.attrs["janela_rotulo_dias"] == 3


def test_rejeita_pico_duplicado():
    dia = pd.Timestamp("2023-02-10")
    base = pd.DataFrame(
        {
            "territorio_id": ["bairro-a"],
            "distrito_id": ["ds-1"],
            "data": [dia],
            "alagou": [0],
            **{c: [1.0] for c in ATRIBUTOS},
        }
    )
    picos = pd.DataFrame(
        {"territorio_id": ["ds-1", "ds-1"], "data": [dia, dia], **{c: [1, 1] for c in NOVAS_FEATURES}}
    )
    with pytest.raises(ValueError, match="duplicados"):
        preparar_mesma_amostra(base, picos)


def test_horas_nao_inteiras_sao_rejeitadas():
    h = _horas("2023-02-09 19:00", "2023-02-10 23:00")
    h.loc[0, "hora"] = pd.Timestamp("2023-02-09 19:30")
    with pytest.raises(ValueError, match="horárias exatas"):
        picos_por_distrito_dia(h)


def test_ultimo_dia_parcial_nao_vira_completo():
    h = _horas("2023-02-09 19:00", "2023-02-11 14:00", mm=1)
    p = picos_por_distrito_dia(h).set_index("data")
    assert p.loc[pd.Timestamp("2023-02-10"), "chuva_pico_6h"] == 6
    assert p.loc[pd.Timestamp("2023-02-11"), list(NOVAS_FEATURES)].isna().all()
