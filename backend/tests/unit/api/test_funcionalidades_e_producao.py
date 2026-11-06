"""Chaves de funcionalidade (ADR 0011, RNF-02) e superfície mínima em produção (T0.2, T0.3). Sem banco."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from climasense.api.main import FUNCOES, criar_app
from climasense.api.routers import saude
from climasense.config import Configuracao
from tests.conftest import configuracao_teste

ROTAS_ATRAS_DE_CHAVE = {
    "func_landing_publica": ["/api/v1/publico/estado", "/api/v1/publico/territorios/busca"],
    "func_comunicados": ["/api/v1/comunicados"],
    "func_avaliacoes": ["/api/v1/avaliacoes"],
    "func_mapa_portatil": ["/api/v1/territorios/mapa-portatil"],
    "func_estatisticas_series": ["/api/v1/series/estatisticas"],
}


def _caminhos(app) -> set[str]:
    return set(app.openapi()["paths"])


def test_todas_as_chaves_nascem_desligadas():
    config = Configuracao(_env_file=None)
    assert set(FUNCOES) == set(ROTAS_ATRAS_DE_CHAVE)
    assert not any(getattr(config, campo) for campo in FUNCOES)


@pytest.mark.parametrize("campo", sorted(ROTAS_ATRAS_DE_CHAVE))
def test_chave_desligada_nao_registra_a_rota_e_responde_404(campo):
    app = criar_app(configuracao_teste())
    cliente = TestClient(app, raise_server_exceptions=False)
    for caminho in ROTAS_ATRAS_DE_CHAVE[campo]:
        assert caminho not in _caminhos(app)
        assert cliente.get(caminho, params={"q": "ab"}).status_code == 404, caminho
    assert not any(c.startswith("/api/v1/publico") for c in app.openapi()["paths"])


@pytest.mark.parametrize("campo", sorted(ROTAS_ATRAS_DE_CHAVE))
def test_chave_ligada_registra_so_a_sua_rota(campo):
    app = criar_app(configuracao_teste(**{campo: True}))
    caminhos = _caminhos(app)
    for caminho in ROTAS_ATRAS_DE_CHAVE[campo]:
        assert caminho in caminhos, caminho
    for outro, rotas in ROTAS_ATRAS_DE_CHAVE.items():
        if outro != campo:
            assert not (set(rotas) & caminhos), outro


def test_rotas_que_ficam_continuam_registradas_com_tudo_desligado():
    caminhos = _caminhos(criar_app(configuracao_teste()))
    for esperado in (
        "/api/v1/health",
        "/api/v1/auth/entrar",
        "/api/v1/series",
        "/api/v1/series/sazonalidade",
        "/api/v1/territorios",
        "/api/v1/admin/login/liberar",
    ):
        assert esperado in caminhos, esperado


# ------------------------------------------------------------------ produção (T0.3)
def _cliente(ambiente: str, checagens: dict) -> TestClient:
    app = criar_app(configuracao_teste(ambiente=ambiente))
    app.dependency_overrides[saude.verificadores] = lambda: checagens
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize("caminho", ["/api/docs", "/api/redoc", "/api/openapi.json"])
def test_producao_nao_expoe_documentacao_nem_contrato(caminho):
    assert _cliente("producao", {}).get(caminho).status_code == 404


@pytest.mark.parametrize("ambiente", ["desenvolvimento", "teste"])
def test_fora_de_producao_a_documentacao_continua(ambiente):
    c = _cliente(ambiente, {})
    assert c.get("/api/docs").status_code == 200
    assert c.get("/api/openapi.json").status_code == 200


def test_health_em_producao_so_diz_ok():
    r = _cliente("producao", {"postgres": lambda: True, "mongo": lambda: True}).get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_health_em_producao_com_dependencia_fora_devolve_falha_sem_detalhes():
    def cai():
        raise ConnectionError("postgresql://u:senha-real@h.invalid/db")

    r = _cliente("producao", {"postgres": cai, "mongo": lambda: True}).get("/api/v1/health")
    assert r.json() == {"status": "falha"}
    assert "senha-real" not in r.text


def test_health_em_desenvolvimento_continua_detalhado():
    r = _cliente("desenvolvimento", {"postgres": lambda: True}).get("/api/v1/health")
    corpo = r.json()
    assert corpo["status"] == "ok" and corpo["ambiente"] == "desenvolvimento"
    assert corpo["bancos"] == {"postgres": "ok"} and "versao" in corpo
