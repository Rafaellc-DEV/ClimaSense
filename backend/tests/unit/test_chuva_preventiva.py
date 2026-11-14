"""Datas de Recife, cobertura e limites reais; somente dados artificiais de teste."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest

from climasense.dominio.estagio import Parametros
from climasense.dominio.simulador import Historico
from climasense.servicos import chuva_preventiva as dias
from climasense.servicos import impacto_territorial as impacto
from tests.unit.test_impacto_territorial import AGORA, fontes, horaria  # noqa: F401


def montar(valor=1, *, agora=AGORA, parametros=None, serie=None, emitida=None):
    serie = serie if serie is not None else [(agora + timedelta(hours=h), valor) for h in range(72)]
    return dias.resumir(
        {"ds-1": {emitida or agora: serie}},
        {"ds-1": "Distrito I", "ds-2": "Distrito II"},
        agora,
        parametros or Parametros(),
    )


def test_72_horas_fuso_recife_e_periodos_parciais():
    resultado = montar()
    assert [d["data"] for d in resultado] == [date(2026, 5, 10) + timedelta(days=h) for h in range(4)]
    assert [d["horas_periodo"] for d in resultado] == [15, 24, 24, 9]
    assert sum(d["horas_periodo"] for d in resultado) == 72
    assert resultado[1]["inicio"].hour == 0 and resultado[1]["inicio"].utcoffset() == -timedelta(hours=3)
    assert resultado[0]["periodo_parcial"] and not resultado[1]["periodo_parcial"]


@pytest.mark.parametrize(
    "total,classe",
    [(24.99, "observacao"), (24.9996, "observacao"), (25, "atencao"), (50, "alerta"), (90, "critico")],
)
def test_limites_inclusivos_existentes(total, classe):
    d = montar(total / 24)[1]["distritos"][0]
    assert d["chuva_prevista_mm"] == pytest.approx(total, abs=0.001)
    assert d["sinalizacao"] == classe


def test_limites_configurados_e_sem_extrapolacao():
    p = replace(Parametros(), chuva_prev_24h_atencao_mm=40)
    r = montar(2, parametros=p)
    assert r[0]["distritos"][0]["chuva_prevista_mm"] == 30
    assert r[0]["distritos"][0]["sinalizacao"] == "observacao"
    assert r[1]["distritos_em_atencao"] == ["ds-1"]


@pytest.mark.parametrize("valor", [None, -1, float("nan"), float("inf")])
def test_hora_invalida_nao_vira_zero(valor):
    serie = horaria(0)
    serie[20] = (serie[20][0], valor)
    d = montar(serie=serie)[1]["distritos"][0]
    assert d["chuva_prevista_mm"] is None and d["horas_validas"] == 23
    assert d["sinalizacao"] == "sem_dados" and d["chuva_intensa"] is None


def test_soma_incompleta_ja_acima_do_limite_sinaliza_com_limite_inferior():
    serie = horaria(3)
    serie.pop(20)
    d = montar(serie=serie)[1]["distritos"][0]
    assert d["chuva_prevista_mm"] is None and d["chuva_disponivel_mm"] == 69
    assert d["sinalizacao"] == "alerta" and d["chuva_intensa"] is True
    assert dias.premissas_do_dia(montar(serie=serie)[1], d, None) is None


def test_duplicata_nao_completa_hora_e_ausencia_de_distrito():
    serie = horaria(0)
    serie.append(serie[20])
    r = montar(serie=serie)
    assert r[1]["distritos"][0]["horas_validas"] == 23
    assert all(d["distritos"][1]["sinalizacao"] == "sem_dados" for d in r)


@pytest.mark.parametrize("idade", [timedelta(hours=6, seconds=1), -timedelta(seconds=1)])
def test_emissao_velha_ou_futura_nao_sinaliza(idade):
    d = montar(10, emitida=AGORA - idade)[1]["distritos"][0]
    assert d["desatualizada"] and d["sinalizacao"] == "sem_dados"


def test_meia_noite_utc_ainda_pertence_ao_dia_anterior_no_recife():
    r = montar(agora=datetime(2026, 1, 1, 1, tzinfo=UTC))
    assert r[0]["data"] == date(2025, 12, 31) and r[0]["horas_periodo"] == 2


def test_hora_parcial_atual_nao_vira_previsao_inteiramente_futura():
    r = montar(agora=AGORA + timedelta(minutes=30), serie=horaria(0))
    assert r[0]["inicio"] == AGORA + timedelta(hours=1)
    assert r[0]["horas_periodo"] == 14 and r[-1]["horas_periodo"] == 10


def test_recorte_parcial_nao_reutiliza_classificacao_ml_do_dia_inteiro(monkeypatch):
    monkeypatch.setattr(impacto.ml, "payload", lambda *a, **kw: pytest.fail("ML em período incompatível"))
    r = impacto.risco_no_periodo(None, AGORA, AGORA.date(), True)
    assert not r["disponivel"] and "parcial" in r["motivo"]


@pytest.mark.usefixtures("fontes")
def test_dia_selecionado_muda_mapa_sem_depender_de_ml_mare_ou_historico(monkeypatch, request):
    estatico = request.getfixturevalue("fontes")
    estatico["historico"] = {b: Historico(None, None) for b in estatico["historico"]}
    monkeypatch.setattr(impacto.cenarios, "mare_prevista", lambda *a: (None, []))
    r = impacto.analisar(None, AGORA, dia=date(2026, 5, 11))
    a, b = r["itens"][:2]
    assert a["sinalizacao_preventiva"] == "critico"
    assert b["sinalizacao_preventiva"] == "observacao"
    assert a["avaliacao"]["chuva_no_horizonte_mm"] == 192
    assert a["avaliacao"]["chuva_observada_72h_mm"] is None
    assert r["dia_selecionado"] == date(2026, 5, 11)
    assert a["classe_alagamento"] == "sem_dados"
    assert not r["ml_alagamento"]["disponivel"]
    with pytest.raises(ValueError, match="72 horas"):
        impacto.analisar(None, AGORA, dia=date(2026, 6, 1))


@pytest.mark.parametrize(
    "fim,prevista,compativel",
    [(AGORA, 8, True), (AGORA - timedelta(minutes=1), 8, False), (AGORA, None, False)],
)
def test_pareamento_apac_so_na_janela_exata_e_com_previsao_preexistente(fim, prevista, compativel):
    class DB:
        def execute(self, sql, params):
            assert "o.emitido_em<=l.lida_em-interval '1 hour'" in str(sql)
            assert "o.coletado_em<=l.lida_em-interval '1 hour'" in str(sql)
            assert "o.territorio_id=l.distrito_id" in str(sql)
            return SimpleNamespace(
                mappings=lambda: [
                    {
                        "distrito_id": "ds-1",
                        "lida_em": fim,
                        "visto_em": AGORA,
                        "valor_mm": 2,
                        "prevista_mm": prevista,
                        "emitido_em": AGORA - timedelta(hours=2),
                        "estacao": "Teste",
                    }
                ]
            )

    r = impacto.comparacoes_recentes(DB(), AGORA)[0]
    assert r["compativel"] is compativel
    assert r["prevista_mm"] == (8 if compativel else None)
    assert r["observada_mm"] == 2
