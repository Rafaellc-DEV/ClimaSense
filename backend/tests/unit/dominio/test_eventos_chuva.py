"""Histórico de eventos de chuva: regras puras (RN-05, RN-13) e a janela de agravo com supressão."""

import uuid
from datetime import UTC, datetime

import pytest

from climasense.dominio import eventos_chuva as dom
from climasense.dominio.evento import RegistroInvalido
from climasense.servicos.relatorio_evento import agravo_na_janela

A, B, C = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()


def _evento(**kw):
    return {"situacao": "encerrado", "aberto_por": A, "encerrado_por": B, **kw}


def test_nome_padrao_usa_a_data_do_recife():
    # 01/05 02:00 UTC ainda é 30/04 no Recife (UTC-3)
    assert dom.nome_padrao(datetime(2026, 5, 1, 2, tzinfo=UTC)) == "Evento de 30/04/2026"


def test_quem_abriu_ou_encerrou_nao_aprova():
    for pessoa in (A, B):
        with pytest.raises(RegistroInvalido) as e:
            dom.validar_aprovador(_evento(), pessoa)
        assert e.value.status == 403
    dom.validar_aprovador(_evento(), C)  # segunda pessoa pode


def test_so_aprova_o_que_foi_encerrado_e_uma_vez():
    with pytest.raises(RegistroInvalido) as e:
        dom.validar_aprovador(_evento(situacao="aberto"), C)
    assert e.value.status == 409
    with pytest.raises(RegistroInvalido) as e:
        dom.validar_aprovador(_evento(situacao="aprovado"), C)
    assert e.value.status == 409


def test_item_comunicado_exige_fonte_e_os_outros_assumem_a_equipe():
    with pytest.raises(RegistroInvalido):
        dom.validar_item("comunicado", "Aviso da APAC", " ", None, None)
    assert dom.validar_item("observacao", " Ruas  alagadas ", None, 3, None) == {
        "tipo": "observacao",
        "texto": "Ruas alagadas",
        "fonte": dom.FONTE_PADRAO,
        "equipes": 3,
        "estagio": None,
    }


@pytest.mark.parametrize(
    "args",
    [
        ("outro", "x", None, None, None),
        ("observacao", "  ", None, None, None),
        ("observacao", "x" * 501, None, None, None),
        ("observacao", "x", None, -1, None),
        ("estagio", "x", None, None, None),
        ("estagio", "x", None, None, "pânico"),
    ],
)
def test_item_invalido(args):
    with pytest.raises(RegistroInvalido) as e:
        dom.validar_item(*args)
    assert e.value.status == 422


def test_situacao_final_obrigatoria_e_pendencia_opcional():
    assert dom.validar_situacao_final(" Normalizado ", "  ") == ("Normalizado", None)
    with pytest.raises(RegistroInvalido):
        dom.validar_situacao_final("  ", "algo")


def test_duracao_e_periodo():
    ini = datetime(2026, 5, 1, 12, tzinfo=UTC)
    assert dom.duracao_horas(ini, datetime(2026, 5, 2, 0, 30, tzinfo=UTC)) == 12.5
    assert dom.duracao_horas(ini, None) is None
    with pytest.raises(RegistroInvalido):
        dom.validar_periodo(ini, datetime(2026, 5, 1, 11, tzinfo=UTC))


def _semana(casos, **kw):
    return {
        "ano": 2026, "semana": 41, "inicio": None, "casos": casos, "confirmados": casos,
        "casos_estimados": 4.2, "ic_inf": 1.0, "ic_sup": 9.0, "nivel_alerta": 2, "rt": 1.1,
        "incompleta": False, **kw,
    }  # fmt: skip


def test_agravo_sem_semana_e_dados_insuficientes_com_a_fonte():
    r = agravo_na_janela("dengue", [], 5, None)
    assert (
        not r["suficiente"] and r["motivo"].startswith("Dados insuficientes") and "infodengue" in r["motivo"]
    )
    sem_casos = agravo_na_janela("dengue", [_semana(None)], 5, None)
    assert not sem_casos["suficiente"]  # ausência não vira zero (RN-01)


def test_agravo_suprime_contagem_pequena_e_o_que_a_revela():
    r = agravo_na_janela("dengue", [_semana(3), _semana(40, semana=42)], 5, None)
    pequena, grande = r["semanas"]
    assert pequena["casos"] is None and pequena["confirmados"] is None and pequena["suprimido"]
    assert pequena["casos_estimados"] is None and pequena["ic_sup"] is None
    assert grande["casos"] == 40 and grande["casos_estimados"] == 4.2
    assert r["total_casos"] is None and r["suprimido"]  # total revelaria a semana pequena


def test_agravo_zero_medido_continua_zero():
    r = agravo_na_janela("leptospirose", [_semana(0)], 5, None)
    assert r["semanas"][0]["casos"] == 0 and r["total_casos"] == 0 and not r["suprimido"]
