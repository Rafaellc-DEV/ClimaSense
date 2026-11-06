"""Limites de login por IP, atraso progressivo e desbloqueio pelo administrador (RNF-01, T0.4).

Estas contas só existem no Postgres de teste. O IP de cada pedido vem de X-Forwarded-For, com o proxy de teste
(10.0.0.1) declarado em PROXIES_CONFIAVEIS."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from climasense.api import autorizacao
from climasense.api.main import criar_app
from climasense.infra.postgres import obter_sessao
from tests.conftest import configuracao_teste, precisa_postgres
from tests.integration.apoio import FUNCOES_LIGADAS, SENHA, Relogio, criar_conta

pytestmark = [precisa_postgres, pytest.mark.integracao]

EMAIL = "coordenacao@recife.pe.gov.br"
ATACANTE = "203.0.113.9"
EQUIPE = "198.51.100.7"
ADMIN_IP = "198.51.100.200"


def _cliente(sessao, relogio: Relogio) -> TestClient:
    app = criar_app(configuracao_teste(proxies_confiaveis="10.0.0.0/8", **FUNCOES_LIGADAS))
    app.dependency_overrides[obter_sessao] = lambda: sessao
    app.dependency_overrides[autorizacao.relogio] = lambda: relogio.agora
    return TestClient(app, client=("10.0.0.1", 40000))


def _entrar(c: TestClient, ip: str, email: str = EMAIL, senha: str = SENHA):
    return c.post(
        "/api/v1/auth/entrar", json={"email": email, "senha": senha}, headers={"X-Forwarded-For": ip}
    )


def _errar(c, relogio, ip, vezes, email=EMAIL, passo_s=31):
    """Erra a senha `vezes` vezes respeitando o atraso progressivo (nenhuma é barrada)."""
    for _ in range(vezes):
        assert _entrar(c, ip, email, "senha errada").status_code == 401
        relogio.avancar(seconds=passo_s)


@pytest.fixture
def relogio():
    return Relogio()


@pytest.fixture
def c(sessao, relogio):
    criar_conta(sessao, EMAIL, ["coordenacao"])
    return _cliente(sessao, relogio)


def _admin(sessao, relogio) -> TestClient:
    criar_conta(sessao, "admin@recife.pe.gov.br", ["administrador"], nome="Admin")
    a = _cliente(sessao, relogio)
    r = _entrar(a, ADMIN_IP, "admin@recife.pe.gov.br")
    assert r.status_code == 200, r.text
    a.headers["X-CSRF-Token"] = a.cookies.get("cs_csrf")
    return a


def test_ip_atacante_nao_trava_a_conta_para_a_equipe(c, relogio):
    _errar(c, relogio, ATACANTE, 5)
    barrado = _entrar(c, ATACANTE)  # nem a senha certa entra do IP bloqueado
    assert barrado.status_code == 429 and "pausado" in barrado.json()["detail"]
    # a coordenação, de outro IP, entra normalmente
    assert _entrar(c, EQUIPE).status_code == 200


def test_atraso_progressivo_pede_para_esperar_e_depois_libera(c, relogio):
    for _ in range(3):
        assert _entrar(c, ATACANTE, EMAIL, "errada").status_code == 401
    r = _entrar(c, ATACANTE, EMAIL, "errada")  # 4ª tentativa sem esperar
    assert r.status_code == 429 and "Aguarde 2 segundos" in r.json()["detail"]
    relogio.avancar(seconds=3)
    assert _entrar(c, ATACANTE).status_code == 200  # a senha certa passa depois da espera


def test_limite_por_ip_vale_para_todas_as_contas_e_o_administrador_libera(sessao, c, relogio):
    for i in range(20):
        _errar(c, relogio, ATACANTE, 1, email=f"ninguem{i}@recife.pe.gov.br")
    r = _entrar(c, ATACANTE)
    assert r.status_code == 429 and "a partir deste acesso" in r.json()["detail"]
    assert _entrar(c, EQUIPE).status_code == 200  # outro IP segue livre

    admin = _admin(sessao, relogio)
    assert admin.post("/api/v1/admin/login/liberar", json={"ip": ATACANTE}).status_code == 200
    relogio.avancar(seconds=1)
    assert _entrar(c, ATACANTE).status_code == 200


def test_administrador_libera_email_bloqueado_no_mesmo_ip(sessao, c, relogio):
    _errar(c, relogio, EQUIPE, 5)  # a equipe errou 5 vezes a partir do seu IP
    assert _entrar(c, EQUIPE).status_code == 429

    admin = _admin(sessao, relogio)
    r = admin.post("/api/v1/admin/login/liberar", json={"email": EMAIL.upper()})
    assert r.status_code == 200 and r.json() == {"email": EMAIL, "ip": None}
    relogio.avancar(seconds=1)
    assert _entrar(c, EQUIPE).status_code == 200

    auditado = sessao.execute(
        text("select detalhes, alvo_tipo from app.auditoria where acao = 'login_liberado'")
    ).one()
    assert auditado.detalhes == {"email": EMAIL, "ip": None} and auditado.alvo_tipo == "login"
    assert sessao.execute(text("select count(*) from app.liberacoes_login")).scalar() == 1


def test_liberar_exige_administrador_e_algum_alvo(sessao, c, relogio):
    assert _entrar(c, EQUIPE).status_code == 200
    c.headers["X-CSRF-Token"] = c.cookies.get("cs_csrf")
    r = c.post("/api/v1/admin/login/liberar", json={"email": "alguem@recife.pe.gov.br"})
    assert r.status_code == 403  # coordenação não libera

    admin = _admin(sessao, relogio)
    assert admin.post("/api/v1/admin/login/liberar", json={}).status_code == 400
    assert admin.post("/api/v1/admin/login/liberar", json={"ip": "isto-nao-e-ip"}).status_code == 422
    assert sessao.execute(text("select count(*) from app.liberacoes_login")).scalar() == 0


def test_sem_proxy_confiavel_o_cabecalho_nao_muda_o_ip(sessao, relogio):
    """Um atacante não consegue escapar do limite trocando X-Forwarded-For, nem culpar outro IP."""
    criar_conta(sessao, EMAIL, ["coordenacao"])
    app = criar_app(configuracao_teste(**FUNCOES_LIGADAS))  # nenhum proxy confiável
    app.dependency_overrides[obter_sessao] = lambda: sessao
    app.dependency_overrides[autorizacao.relogio] = lambda: relogio.agora
    c = TestClient(app, client=("203.0.113.50", 40000))
    for i in range(5):
        assert _entrar(c, f"9.9.9.{i}", EMAIL, "errada").status_code == 401
        relogio.avancar(seconds=31)
    assert _entrar(c, "8.8.8.8").status_code == 429
