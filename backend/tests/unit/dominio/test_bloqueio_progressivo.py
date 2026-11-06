"""Atraso progressivo e limite configurável do bloqueio (RNF-01, T0.4)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from climasense.dominio.bloqueio import Tentativa, bloqueado_ate, espera_ate

T0 = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)


def _falhas(n: int, passo_s: int = 1) -> list[Tentativa]:
    return [Tentativa(T0 + timedelta(seconds=i * passo_s), False) for i in range(n)]


def test_falhas_livres_nao_obrigam_a_esperar():
    assert espera_ate(_falhas(2), T0 + timedelta(seconds=2), livres=2, teto_s=30) is None


def test_espera_dobra_a_cada_falha_com_teto():
    ultima = T0 + timedelta(seconds=9)
    # 3 falhas (1 acima das livres): 2 s; 4: 4 s; 5: 8 s; 10 falhas: teto de 30 s
    assert espera_ate(_falhas(3), T0 + timedelta(seconds=2), 2, 30) == T0 + timedelta(seconds=2 + 2)
    assert espera_ate(_falhas(4), T0 + timedelta(seconds=3), 2, 30) == T0 + timedelta(seconds=3 + 4)
    assert espera_ate(_falhas(5), T0 + timedelta(seconds=4), 2, 30) == T0 + timedelta(seconds=4 + 8)
    assert espera_ate(_falhas(10), ultima, 2, 30) == ultima + timedelta(seconds=30)


def test_espera_acaba_e_o_sucesso_zera():
    f = _falhas(3)
    assert espera_ate(f, T0 + timedelta(seconds=10), 2, 30) is None
    com_sucesso = [*f, Tentativa(T0 + timedelta(seconds=3), True)]
    assert espera_ate(com_sucesso, T0 + timedelta(seconds=3), 2, 30) is None


def test_falhas_antigas_saem_da_janela():
    assert espera_ate(_falhas(8), T0 + timedelta(minutes=20), 2, 30) is None


def test_limite_do_bloqueio_e_configuravel():
    f = _falhas(20)
    agora = T0 + timedelta(seconds=30)
    assert bloqueado_ate(f, agora, limite=20) == T0 + timedelta(seconds=19, minutes=15)
    assert bloqueado_ate(f[:19], agora, limite=20) is None
    assert bloqueado_ate(f[:5], agora) is not None  # padrão continua 5
