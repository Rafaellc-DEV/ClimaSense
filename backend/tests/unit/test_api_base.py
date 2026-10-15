from datetime import date

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
from pydantic import BaseModel

from climasense.api.envelope import FonteMeta, Meta, RecorteMeta, RespostaDados
from climasense.api.main import criar_app
from climasense.api.routers import saude
from climasense.config import ConfiguracaoAusente
from climasense.dominio.recorte import Recorte
from tests.conftest import configuracao_teste


def _falha():
    raise ConnectionError("mongodb+srv://u:senha-real@cluster.invalid/ recusou")


def _sem_config():
    raise ConfiguracaoAusente("Configure MONGO_URI no arquivo .env.")


@pytest.fixture
def app():
    app = criar_app(configuracao_teste())
    rota = APIRouter(prefix="/api/v1/_teste")

    class Entrada(BaseModel):
        email: str
        idade: int

    @rota.post("/validar")
    def validar(e: Entrada):
        return e

    @rota.get("/quebrar")
    def quebrar():
        raise RuntimeError("postgresql://u:senha-real@h.invalid/db caiu")

    @rota.get("/recorte")
    def recorte():
        Recorte("ds-9", date(2026, 1, 1), date(2026, 1, 2))

    app.include_router(rota)
    return app


def _cliente(app, checagens):
    app.dependency_overrides[saude.verificadores] = lambda: checagens
    return TestClient(app, raise_server_exceptions=False)


def test_health_ok(app):
    r = _cliente(app, {"postgres": lambda: True, "mongo": lambda: True}).get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {
        "status": "ok",
        "versao": "0.1.0",
        "ambiente": "teste",
        "bancos": {"postgres": "ok", "mongo": "ok"},
    }


def test_health_com_banco_fora_do_ar_nao_vaza_detalhes(app):
    r = _cliente(app, {"postgres": lambda: True, "mongo": _falha}).get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "degradado"
    assert r.json()["bancos"]["mongo"] == "indisponivel"
    assert "senha-real" not in r.text


def test_health_sem_configuracao(app):
    r = _cliente(app, {"postgres": _sem_config, "mongo": _sem_config}).get("/api/v1/health")
    assert r.json()["bancos"] == {"postgres": "nao_configurado", "mongo": "nao_configurado"}


def test_erros_sao_problem_json_em_portugues(app):
    c = _cliente(app, {})
    r = c.get("/api/v1/nao-existe")
    assert r.status_code == 404
    assert r.headers["content-type"] == "application/problem+json"
    assert r.json()["detail"] == "O endereço pedido não existe."

    r = c.post("/api/v1/_teste/validar", json={"email": "a@b.c"})
    assert r.status_code == 422
    assert r.json()["detail"] == "Confira os campos: idade."


def test_erro_inesperado_nao_mostra_pilha_nem_conexao(app):
    r = _cliente(app, {}).get("/api/v1/_teste/quebrar")
    assert r.status_code == 500
    assert r.json()["detail"] == "Algo deu errado do nosso lado. Tente de novo em alguns minutos."
    assert "senha-real" not in r.text and "Traceback" not in r.text


def test_recorte_invalido_vira_400_com_mensagem(app):
    r = _cliente(app, {}).get("/api/v1/_teste/recorte")
    assert r.status_code == 400
    assert "ds-9" in r.json()["detail"]


def test_cabecalhos_de_seguranca(app):
    r = _cliente(app, {"postgres": lambda: True, "mongo": lambda: True}).get("/api/v1/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]


def test_openapi_disponivel(app):
    r = _cliente(app, {}).get("/api/openapi.json")
    assert r.status_code == 200
    assert "/api/v1/health" in r.json()["paths"]


def test_envelope_exige_ao_menos_uma_fonte_e_marca_dados_insuficientes():
    with pytest.raises(ValueError):
        Meta(fontes=[])
    resposta = RespostaDados[list[int]](
        dados=[],
        meta=Meta(
            fontes=[
                FonteMeta(
                    id="vacinacao", nome="Dados Abertos do Recife", tipo="observada", status="atualizada"
                )
            ],
            recorte=RecorteMeta(territorio_id="ds-4", granularidade="distrito"),
            dados_insuficientes=True,
        ),
    )
    corpo = resposta.model_dump(mode="json")
    assert corpo["meta"]["dados_insuficientes"] is True
    assert corpo["meta"]["fontes"][0]["tipo"] == "observada"
