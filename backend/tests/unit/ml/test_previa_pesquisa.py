"""Prévia de pesquisa não quebra gate operacional nem abre rota em produção.

Sem rede, sem banco e sem arquivos joblib.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from climasense.api.erros import ErroClimaSense
from climasense.api.routers import risco_alagamento
from climasense.config import Configuracao
from climasense.ml.alagamento import servico


def test_previa_local_desligada_por_padrao():
    cfg = Configuracao(_env_file=None, ambiente="desenvolvimento")
    assert cfg.ml_previa_experimental_local is False


def test_previa_local_bloqueada_mesmo_com_flag_em_producao():
    cfg = Configuracao(_env_file=None, ambiente="producao", ml_previa_experimental_local=True)
    with pytest.raises(ErroClimaSense) as erro:
        risco_alagamento.previa_local(_=None, config=cfg, db=None, agora=datetime(2026, 11, 13, tzinfo=UTC))
    assert erro.value.status == 404


def test_previa_local_bloqueada_sem_flag_em_desenvolvimento():
    cfg = Configuracao(_env_file=None, ambiente="desenvolvimento", ml_previa_experimental_local=False)
    with pytest.raises(ErroClimaSense) as erro:
        risco_alagamento.previa_local(_=None, config=cfg, db=None, agora=datetime(2026, 11, 13, tzinfo=UTC))
    assert erro.value.status == 404


def test_payload_previa_nao_muda_publicavel(monkeypatch):
    art = SimpleNamespace(publicavel=False, motivo="AUC-PR abaixo da referência")
    monkeypatch.setattr(servico.armazenamento, "carregar_em_cache", lambda: art)
    monkeypatch.setattr(servico.armazenamento, "compativel", lambda a: a is art)
    monkeypatch.setattr(
        servico,
        "risco_por_territorio",
        lambda db, agora, artefato, **kwargs: {
            "bairro-a": {"classe": "alto", "confianca": "baixa", "fatores": ["Pesquisa"]}
        },
    )
    monkeypatch.setattr(servico, "descricao_modelo", lambda a: {"versao": "0.2.0"})
    r = servico.payload_previa_local(None, datetime(2026, 11, 13, tzinfo=UTC))
    assert r["disponivel"] is True
    assert r["itens"][0]["classe"] == "alto"
    assert "NÃO VALIDADA" in r["motivo"]
    assert art.publicavel is False


@pytest.mark.parametrize(
    "ambiente,habilitada,papel,status",
    [
        ("producao", True, "administrador", 404),
        ("teste", True, "administrador", 404),
        ("desenvolvimento", False, "administrador", 404),
        ("desenvolvimento", True, "analista", 403),
        ("desenvolvimento", True, "observador", 403),
        ("desenvolvimento", True, None, 401),
        ("desenvolvimento", True, "administrador", 200),
    ],
)
def test_contrato_http_previa_sem_banco(monkeypatch, ambiente, habilitada, papel, status):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from climasense.api import autorizacao
    from climasense.api.deps import configuracao
    from climasense.api.erros import registrar_tratadores
    from climasense.infra.postgres import obter_sessao

    app = FastAPI()
    registrar_tratadores(app)
    app.include_router(risco_alagamento.router, prefix="/api/v1")
    cfg = Configuracao(_env_file=None, ambiente=ambiente, ml_previa_experimental_local=habilitada)
    app.dependency_overrides[configuracao] = lambda: cfg
    app.dependency_overrides[obter_sessao] = lambda: None

    def contexto(*args, **kwargs):
        if papel is None:
            raise ErroClimaSense(401, "Entre para continuar.")
        return SimpleNamespace(usuario=SimpleNamespace(papeis=[papel]))

    monkeypatch.setattr(autorizacao, "_contexto", contexto)
    chamadas = []

    def previa(*args):
        chamadas.append(True)
        return {"disponivel": False, "motivo": "Modelo ausente", "modelo": None, "itens": []}

    monkeypatch.setattr(servico, "payload_previa_local", previa)
    monkeypatch.setattr(
        risco_alagamento.servico_fontes,
        "meta",
        lambda *args: {"id": args[1], "nome": args[1], "tipo": "prevista", "status": "planejada"},
    )
    resposta = TestClient(app).get("/api/v1/risco-alagamento/previa-local")
    assert resposta.status_code == status
    assert bool(chamadas) == (status == 200)
    if status == 200:
        assert resposta.json()["dados"]["disponivel"] is False
        assert resposta.json()["meta"]["dados_insuficientes"] is True
