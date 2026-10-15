"""Apoio aos testes de API: cliente HTTP, relógio controlável e criação de contas."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from climasense.api import autorizacao
from climasense.api.main import criar_app
from climasense.infra.postgres import obter_sessao
from climasense.servicos.usuarios import ServicoUsuarios
from tests.conftest import configuracao_teste

SENHA = "maré alta no capibaribe"


class Relogio:
    def __init__(self) -> None:
        self.agora = datetime(2026, 10, 15, 20, 0, tzinfo=UTC)

    def avancar(self, **delta) -> None:
        self.agora += timedelta(**delta)


def cliente(sessao, relogio: Relogio) -> TestClient:
    app = criar_app(configuracao_teste())
    app.dependency_overrides[obter_sessao] = lambda: sessao
    app.dependency_overrides[autorizacao.relogio] = lambda: relogio.agora
    return TestClient(app, raise_server_exceptions=True)


def criar_conta(
    sessao, email: str, papeis: list[str], troca_obrigatoria: bool = False, nome: str = "Pessoa da Equipe"
):
    conta = ServicoUsuarios(sessao).criar(nome, email, papeis, autor=None, senha_inicial=SENHA)
    conta.usuario.troca_senha_obrigatoria = troca_obrigatoria
    sessao.commit()
    return conta.usuario


def entrar(c: TestClient, email: str, senha: str = SENHA):
    r = c.post("/api/v1/auth/entrar", json={"email": email, "senha": senha})
    if r.status_code == 200:
        c.headers["X-CSRF-Token"] = c.cookies.get("cs_csrf")
    return r
