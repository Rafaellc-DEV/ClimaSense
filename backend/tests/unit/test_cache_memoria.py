"""Cache em memória com TTL (infra/cache.py): expira, respeita a chave, não esconde ausência e é desligável."""

from __future__ import annotations

import pytest

from climasense.infra import cache


@pytest.fixture(autouse=True)
def _cache_ligado(monkeypatch):
    monkeypatch.setattr(cache, "ativo", True)
    relogio = {"t": 1000.0}
    monkeypatch.setattr(cache, "_relogio", lambda: relogio["t"])
    cache.limpar()
    yield relogio
    cache.limpar()


def _contador():
    chamadas = []

    def fabrica(valor):
        def f():
            chamadas.append(valor)
            return valor

        return f

    return chamadas, fabrica


def test_guarda_e_devolve_o_mesmo_resultado(_cache_ligado):
    chamadas, f = _contador()
    assert cache.obter("e", "k", 60, f({"a": 1})) == {"a": 1}
    assert cache.obter("e", "k", 60, f({"a": 2})) == {"a": 1}  # não recalculou
    assert len(chamadas) == 1


def test_expira_depois_do_ttl_e_recalcula(_cache_ligado):
    chamadas, f = _contador()
    cache.obter("e", "k", 60, f(1))
    _cache_ligado["t"] += 59.9
    assert cache.obter("e", "k", 60, f(2)) == 1
    _cache_ligado["t"] += 0.2  # passou de 60 s
    assert cache.obter("e", "k", 60, f(3)) == 3
    assert chamadas == [1, 3]


def test_chave_com_parametros_diferentes_nao_se_mistura(_cache_ligado):
    _, f = _contador()
    assert cache.obter("e", ("ds-1", 2026), 60, f("a")) == "a"
    assert cache.obter("e", ("ds-2", 2026), 60, f("b")) == "b"
    assert cache.obter("e", ("ds-1", 2025), 60, f("c")) == "c"
    assert cache.obter("outro", ("ds-1", 2026), 60, f("d")) == "d"


def test_ausencia_tambem_e_guardada_mas_expira(_cache_ligado):
    chamadas, _ = _contador()

    def sem_dado():
        chamadas.append(1)
        return None

    assert cache.obter("e", "k", 60, sem_dado) is None
    assert cache.obter("e", "k", 60, sem_dado) is None
    assert len(chamadas) == 1
    _cache_ligado["t"] += 61  # a carga chegou: o "Dados insuficientes" some em até 1 TTL
    assert cache.obter("e", "k", 60, lambda: 7) == 7


def test_falha_da_fabrica_nao_guarda_nada(_cache_ligado):
    def quebra():
        raise RuntimeError("banco fora")

    with pytest.raises(RuntimeError):
        cache.obter("e", "k", 60, quebra)
    assert cache.obter("e", "k", 60, lambda: 5) == 5


def test_ttl_zero_ou_cache_desligado_sempre_calcula(_cache_ligado, monkeypatch):
    chamadas, f = _contador()
    cache.obter("e", "k", 0, f(1))
    cache.obter("e", "k", 0, f(2))
    monkeypatch.setattr(cache, "ativo", False)
    cache.obter("e", "k2", 60, f(3))
    cache.obter("e", "k2", 60, f(4))
    assert chamadas == [1, 2, 3, 4]


def test_limpar_um_espaco_nao_toca_nos_outros(_cache_ligado):
    _, f = _contador()
    cache.obter("a", "k", 60, f(1))
    cache.obter("b", "k", 60, f(2))
    cache.limpar("a")
    assert cache.obter("a", "k", 60, f(9)) == 9
    assert cache.obter("b", "k", 60, f(8)) == 2


def test_ttls_documentados_ordenados():
    assert cache.VIVO_S <= 60 < cache.MEDIO_S < cache.CARGA_S
