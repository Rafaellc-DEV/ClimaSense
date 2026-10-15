from datetime import UTC, datetime, timedelta

import pytest

from climasense.auth import senhas
from climasense.dominio.bloqueio import Tentativa, bloqueado_ate
from climasense.dominio.papeis import Papel, PapelInvalido, Permissao, normalizar, permissoes, pode
from climasense.dominio.senha import problemas_da_senha

T0 = datetime(2026, 10, 15, 20, 0, tzinfo=UTC)


# ---------------------------------------------------------------- papéis (RF-03)
def test_permissoes_sao_cumulativas():
    analista = permissoes(["analista"])
    revisor = permissoes(["revisor"])
    coordenacao = permissoes(["coordenacao"])
    assert analista < revisor < coordenacao
    assert Permissao.PUBLICAR in coordenacao and Permissao.PUBLICAR not in revisor
    assert Permissao.ADMINISTRAR not in coordenacao
    assert permissoes(["administrador"]) == frozenset(Permissao)


def test_acumulo_de_papeis_soma_permissoes():
    assert pode(["analista", "administrador"], Permissao.EXECUTAR_ETL)
    assert normalizar(["administrador", "analista", "analista"]) == [Papel.ANALISTA, Papel.ADMINISTRADOR]


@pytest.mark.parametrize("ruim", [[], ["dono"], ["Analista"]])
def test_papeis_invalidos(ruim):
    with pytest.raises(PapelInvalido):
        normalizar(ruim)
    assert not pode(ruim, Permissao.CONSULTAR)


# ---------------------------------------------------------------- política de senha
def test_senha_curta_ou_obvia_e_recusada_com_mensagem_simples():
    assert problemas_da_senha("abc") == ["Use pelo menos 10 caracteres. Uma frase curta funciona bem."]
    assert "fácil de adivinhar" in problemas_da_senha("1234567890")[0]
    assert "Não use o seu e-mail na senha." in problemas_da_senha(
        "rafaelcosta2026!", "rafaelcosta@recife.pe.gov.br"
    )
    assert problemas_da_senha("maré alta no capibaribe") == []


def test_hash_argon2_e_senha_temporaria():
    h = senhas.gerar_hash("maré alta no capibaribe")
    assert h.startswith("$argon2id$")
    assert senhas.conferir("maré alta no capibaribe", h)
    assert not senhas.conferir("outra senha qualquer", h)
    assert not senhas.conferir("qualquer", None)
    assert not senhas.conferir("qualquer", "hash-corrompido")
    temporaria = senhas.senha_temporaria()
    assert len(temporaria) == 14 and temporaria.count("-") == 2
    assert not set(temporaria) & set("0o1li")


# ---------------------------------------------------------------- bloqueio (RF-02.3)
def falhas(n, inicio=T0, passo=timedelta(minutes=1)):
    return [Tentativa(inicio + passo * i, False) for i in range(n)]


def test_quatro_falhas_nao_bloqueiam_e_a_quinta_bloqueia_por_15_minutos():
    assert bloqueado_ate(falhas(4), T0 + timedelta(minutes=4)) is None
    quinta = T0 + timedelta(minutes=4)
    assert bloqueado_ate(falhas(5), quinta) == quinta + timedelta(minutes=15)


def test_bloqueio_termina_depois_de_15_minutos():
    quinta = T0 + timedelta(minutes=4)
    assert bloqueado_ate(falhas(5), quinta + timedelta(minutes=14, seconds=59)) is not None
    assert bloqueado_ate(falhas(5), quinta + timedelta(minutes=15)) is None


def test_falhas_espalhadas_em_mais_de_15_minutos_nao_bloqueiam():
    assert bloqueado_ate(falhas(5, passo=timedelta(minutes=4)), T0 + timedelta(minutes=16)) is None


def test_sucesso_zera_a_contagem():
    historico = (
        falhas(4) + [Tentativa(T0 + timedelta(minutes=5), True)] + falhas(4, T0 + timedelta(minutes=6))
    )
    assert bloqueado_ate(historico, T0 + timedelta(minutes=10)) is None
