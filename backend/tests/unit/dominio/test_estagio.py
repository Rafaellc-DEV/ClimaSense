"""F1: sugestão de estágio operacional a partir dos limiares (domínio puro, sem banco)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from climasense.dominio import estagio as dom

AGORA = datetime(2026, 11, 4, 15, 0, tzinfo=UTC)
P = dom.Parametros()


def _ins(**extra) -> dom.Insumos:
    base = {
        "chuva_24h_mm": 2.0,
        "chuva_prev_24h_mm": 5.0,
        "chuva_prev_72h_mm": 10.0,
        "horas_previstas_72h": 72,
        "mare_max_m": 0.4,
        "mare_no_pico_m": 0.3,
    }
    base.update(extra)
    return dom.Insumos(**base)


def test_sem_gatilho_e_observacao_com_motivo():
    s = dom.sugerir(_ins(), P)
    assert s.estagio == "observacao" and not s.faltando
    assert "Nenhum gatilho" in s.motivos[0]


@pytest.mark.parametrize(
    ("campo", "valor", "esperado"),
    [
        ("chuva_prev_24h_mm", 25.0, "atencao"),
        ("chuva_prev_24h_mm", 60.0, "alerta"),
        ("chuva_prev_24h_mm", 90.0, "critico"),
        ("chuva_prev_72h_mm", 100.0, "alerta"),
        ("chuva_24h_mm", 55.0, "alerta"),
    ],
)
def test_limiares_de_chuva(campo, valor, esperado):
    s = dom.sugerir(_ins(**{campo: valor}), P)
    assert s.estagio == esperado
    assert any("acima do limite" in m for m in s.motivos)


def test_maior_gatilho_vence():
    s = dom.sugerir(_ins(chuva_prev_24h_mm=30.0, chuva_prev_72h_mm=160.0), P)
    assert s.estagio == "critico"


def test_falta_previsao_ou_mare_e_sem_dados_nunca_observacao():
    """RN-01: faltando insumo, sem_dados — mesmo que a chuva que existe seja baixa."""
    for falta in ("chuva_prev_24h_mm", "chuva_prev_72h_mm", "mare_max_m"):
        s = dom.sugerir(_ins(**{falta: None}), P)
        assert s.estagio == "sem_dados", falta
        assert s.faltando and "Faltam dados" in s.motivos[0]


def test_sem_dados_ainda_conta_o_sinal_que_disparou():
    s = dom.sugerir(_ins(mare_max_m=None, mare_no_pico_m=None, chuva_24h_mm=95.0), P)
    assert s.estagio == "sem_dados"
    assert "pelo menos crítico" in s.motivos[0]


def test_sem_chuva_recente_avisa_mas_nao_bloqueia():
    s = dom.sugerir(_ins(chuva_24h_mm=None, chuva_prev_24h_mm=30.0), P)
    assert s.estagio == "atencao"
    assert any("últimas 24 h" in m and "não entrou" in m for m in s.motivos)


def test_mare_alta_no_pico_sobe_um_nivel_so_a_partir_de_atencao():
    assert dom.sugerir(_ins(chuva_prev_24h_mm=30.0, mare_no_pico_m=0.8), P).estagio == "alerta"
    assert dom.sugerir(_ins(mare_no_pico_m=0.8), P).estagio == "observacao"
    critico = dom.sugerir(_ins(chuva_prev_24h_mm=95.0, mare_no_pico_m=0.8), P)
    assert critico.estagio == "critico"  # não passa do topo


def test_ocorrencias_do_bairro_sobem_um_nivel():
    s = dom.sugerir(_ins(chuva_prev_24h_mm=30.0, ocorrencias_historicas=5), P)
    assert s.estagio == "alerta" and any("ocorrência" in m for m in s.motivos)
    assert dom.sugerir(_ins(chuva_prev_24h_mm=30.0, ocorrencias_historicas=1), P).estagio == "atencao"
    # zero ocorrências registradas é diferente de fonte sem carga (None), e nenhum dos dois sobe
    assert dom.sugerir(_ins(chuva_prev_24h_mm=30.0, ocorrencias_historicas=None), P).estagio == "atencao"


def test_risco_ml_so_sobe_e_e_opcional():
    assert dom.sugerir(_ins(risco_ml="alto"), P).estagio == "alerta"
    baixo = dom.sugerir(_ins(chuva_prev_24h_mm=60.0, risco_ml="baixo"), P)
    assert baixo.estagio == "alerta" and any("experimental" in m for m in baixo.motivos)
    assert dom.sugerir(_ins(risco_ml=None), P).estagio == "observacao"


def test_bairro_herdado_diz_de_onde_vem_a_chuva():
    s = dom.sugerir(_ins(herdado_de="Distrito Sanitário IV"), P)
    assert any("herda" in m and "Distrito Sanitário IV" in m for m in s.motivos)


def test_limiares_configuraveis():
    p = dom.Parametros(
        chuva_prev_24h_atencao_mm=3.0, chuva_prev_24h_alerta_mm=4.0, chuva_prev_24h_critico_mm=5.0
    )
    assert dom.sugerir(_ins(), p).estagio == "critico"


def test_parametros_validados_e_serializados():
    assert dom.problemas_parametros(P) == []
    ruim = dom.Parametros(chuva_prev_24h_atencao_mm=60.0, mare_alta_m=0)
    erros = dom.problemas_parametros(ruim)
    assert any("menor que o de alerta" in e for e in erros) and any("maré" in e.lower() for e in erros)
    de_volta = dom.Parametros.de_dict({**P.como_dict(), "desconhecido": 1, "mare_alta_m": None})
    assert de_volta == P


def test_acumulado_previsto_exige_horas_minimas():
    chuva = [(AGORA + timedelta(hours=h), 1.0) for h in range(60)]
    assert dom.acumulado_previsto(chuva, AGORA, 24) == (24.0, 24)
    assert dom.acumulado_previsto(chuva, AGORA, 72) == (60.0, 60)
    curta = [(AGORA + timedelta(hours=h), 1.0) for h in range(30)]
    assert dom.acumulado_previsto(curta, AGORA, 72) == (None, 30)  # pouca previsão não vira “pouca chuva”
    com_lacuna = [(t, None if i % 2 else v) for i, (t, v) in enumerate(chuva)]
    assert dom.acumulado_previsto(com_lacuna, AGORA, 24)[0] is None


def test_mare_perto_do_pico():
    chuva = [(AGORA + timedelta(hours=h), float(h == 10) * 8.0) for h in range(72)]
    pico = dom.pico(chuva, AGORA)
    assert pico == AGORA + timedelta(hours=10)
    mare = [(AGORA + timedelta(hours=h), 0.1 * h) for h in range(20)]
    assert dom.mare_perto_do_pico(mare, pico, 3) == pytest.approx(1.3)
    assert dom.mare_perto_do_pico(mare, None, 3) is None
    assert dom.pico([(AGORA, 0.0)], AGORA) is None


def test_insumos_dos_distritos_ficam_em_cache_por_60_s(monkeypatch):
    """Duas leituras seguidas calculam uma vez; com o cache desligado ou vencido, calculam de novo."""
    from datetime import UTC, datetime

    from climasense.servicos import estagios

    chamadas = []
    monkeypatch.setattr(
        estagios,
        "_calcular_insumos_distritos",
        lambda db, ds, agora, p: chamadas.append(1) or {"ds-1": ("x", {})},
    )
    monkeypatch.setattr(estagios, "CACHE_INSUMOS_S", 60.0)
    estagios.limpar_cache_insumos()
    agora = datetime(2026, 11, 5, 15, 30, tzinfo=UTC)
    p = estagios.dom.Parametros()
    assert estagios.insumos_distritos(None, ["ds-1"], agora, p) == estagios.insumos_distritos(
        None, ["ds-1"], agora, p
    )
    assert len(chamadas) == 1
    estagios.insumos_distritos(None, ["ds-2"], agora, p)  # outro conjunto de distritos
    assert len(chamadas) == 2
    monkeypatch.setattr(estagios, "CACHE_INSUMOS_S", 0.0)  # desligado: sempre calcula
    estagios.insumos_distritos(None, ["ds-1"], agora, p)
    assert len(chamadas) == 3
    estagios.limpar_cache_insumos()
