"""Matriz de autorização (T3.6): para TODA rota da API e TODO papel, confere a resposta esperada.

Uma rota nova sem permissão declarada (`exige(...)`) e fora das listas abaixo faz este teste falhar.
"""

import re
import uuid

import pytest

from climasense.api.autorizacao import contexto_autenticado
from climasense.api.main import PREFIXO, ROTEADORES
from climasense.dominio.papeis import Papel, pode
from tests.conftest import precisa_postgres
from tests.integration.apoio import Relogio, cliente, criar_conta, entrar

pytestmark = [precisa_postgres, pytest.mark.integracao]

PUBLICAS = {
    ("GET", "/api/v1/health"),
    ("POST", "/api/v1/auth/entrar"),
    ("GET", "/api/v1/publico/estado"),
    ("GET", "/api/v1/publico/avisos"),
    ("GET", "/api/v1/publico/avisos/{aviso_id}"),
    ("GET", "/api/v1/publico/fontes"),
    ("GET", "/api/v1/publico/territorios/busca"),
}


def _rotas():
    for roteador in ROTEADORES:
        for rota in roteador.routes:
            for metodo in rota.methods:
                deps = [d.call for d in rota.dependant.dependencies]
                permissao = next(
                    (getattr(d, "permissao", None) for d in deps if hasattr(d, "permissao")), None
                )
                autenticada = contexto_autenticado in deps
                yield metodo, PREFIXO + rota.path, permissao, autenticada


ROTAS = list(_rotas())


def test_toda_rota_declara_como_e_protegida():
    soltas = [(m, p) for m, p, perm, aut in ROTAS if perm is None and not aut and (m, p) not in PUBLICAS]
    assert not soltas, f"Rotas sem exige(...) nem contexto_autenticado: {soltas}"


def _url(caminho: str) -> str:
    return re.sub(r"\{[^}]+\}", str(uuid.uuid4()), caminho)


@pytest.mark.parametrize("papel", list(Papel), ids=lambda p: p.value)
def test_matriz_rota_por_papel(sessao, papel):
    c = cliente(sessao, Relogio())
    criar_conta(sessao, f"{papel.value}@recife.pe.gov.br", [papel.value])
    entrar(c, f"{papel.value}@recife.pe.gov.br")
    for metodo, caminho, permissao, _ in ROTAS:
        if permissao is None:
            continue
        r = c.request(metodo, _url(caminho), json={})
        if pode([papel.value], permissao):
            assert r.status_code not in (401, 403), (
                f"{papel} deveria acessar {metodo} {caminho}: {r.status_code}"
            )
        else:
            assert r.status_code == 403, f"{papel} NÃO deveria acessar {metodo} {caminho}: {r.status_code}"
            assert r.json()["detail"] == "Você não tem permissão para esta ação. Fale com a coordenação."


def test_sem_login_toda_rota_protegida_responde_401(sessao):
    c = cliente(sessao, Relogio())
    for metodo, caminho, permissao, autenticada in ROTAS:
        if permissao or autenticada:
            assert c.request(metodo, _url(caminho), json={}).status_code == 401, caminho
