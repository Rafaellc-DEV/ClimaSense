"""Fixtures comuns. Os testes nunca leem o .env do desenvolvedor: a configuração é montada aqui.

Integração (Postgres real): defina DATABASE_URL_TESTE apontando para um banco de testes descartável,
ex.: postgresql://climasense:climasense@localhost:5432/climasense_teste (docker-compose do projeto).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config as ConfigAlembic
from sqlalchemy import text
from sqlalchemy.engine import make_url

from climasense.config import Configuracao
from climasense.infra.postgres import criar_engine, fabrica_sessoes, normalizar_url

RAIZ = Path(__file__).resolve().parents[2]
BACKEND = RAIZ / "backend"
DADOS_TERRITORIO = RAIZ / "data" / "territorio"


def configuracao_teste(**extra) -> Configuracao:
    base = {"ambiente": "teste", "session_secret": "chave-de-teste-nao-usar-em-producao-0123456789"}
    base.update(extra)
    return Configuracao(_env_file=None, **base)


@pytest.fixture
def config() -> Configuracao:
    return configuracao_teste()


@pytest.fixture(scope="session")
def distritos_oficiais() -> list[dict]:
    """Features reais do GeoJSON oficial enriquecido (data/territorio)."""
    return json.loads((DADOS_TERRITORIO / "distritos-enriquecidos.geojson").read_text(encoding="utf-8"))[
        "features"
    ]


# ---------------------------------------------------------------- integração com Postgres real
URL_TESTE = os.getenv("DATABASE_URL_TESTE")
precisa_postgres = pytest.mark.skipif(
    not URL_TESTE, reason="defina DATABASE_URL_TESTE para os testes de integração"
)


def _alembic(url: str) -> ConfigAlembic:
    cfg = ConfigAlembic(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    cfg.cmd_opts = type("Opcoes", (), {"x": [f"url={url}"]})()
    return cfg


def recriar_banco(url: str):
    engine = criar_engine(url)
    with engine.begin() as c:
        c.execute(
            text(
                "drop schema if exists gold cascade; drop schema if exists silver cascade; drop schema if exists app cascade"
            )
        )
        c.execute(text("drop table if exists public.alembic_version"))
    command.upgrade(_alembic(url), "head")
    return engine


@pytest.fixture(scope="session")
def engine_teste():
    if not URL_TESTE:
        pytest.skip("defina DATABASE_URL_TESTE para os testes de integração")
    engine = recriar_banco(URL_TESTE)
    yield engine
    engine.dispose()


SENHA_PAPEL_APP_TESTE = "senha-do-papel-de-teste-nao-usar-fora-daqui"


@pytest.fixture(scope="session")
def engine_app(engine_teste):
    """Engine do papel `climasense_app` (criado pela 0014, sem senha): dá a senha de teste e conecta como ele."""
    with engine_teste.begin() as c:
        c.execute(text(f"alter role climasense_app login password '{SENHA_PAPEL_APP_TESTE}'"))
    url = make_url(normalizar_url(URL_TESTE)).set(username="climasense_app", password=SENHA_PAPEL_APP_TESTE)
    engine = criar_engine(url.render_as_string(hide_password=False))
    yield engine
    engine.dispose()


@pytest.fixture
def sessao(engine_teste, request):
    """Sessão com transação desfeita ao fim de cada teste (o banco volta limpo).

    TESTES_COMO_APP=1 roda as rotas como `climasense_app` (privilégio mínimo, ADR 0014); o padrão é o dono,
    porque muitos testes semeiam silver e gold, que a aplicação só lê.
    """
    if os.getenv("TESTES_COMO_APP") == "1":
        engine_teste = request.getfixturevalue("engine_app")
    conexao = engine_teste.connect()
    transacao = conexao.begin()
    s = fabrica_sessoes(engine_teste)(bind=conexao, join_transaction_mode="create_savepoint")
    try:
        yield s
    finally:
        s.close()
        transacao.rollback()
        conexao.close()


@pytest.fixture(autouse=True)
def _sem_cache_de_insumos(monkeypatch):
    """O cache de 60 s dos insumos de estágio faria um teste enxergar o dado do anterior: desligado por padrão."""
    from climasense.servicos import estagios

    estagios.limpar_cache_insumos()
    monkeypatch.setattr(estagios, "CACHE_INSUMOS_S", 0.0)


@pytest.fixture(autouse=True)
def _sem_cache_do_simulador():
    """O cache dos insumos estáticos do simulador faria um teste enxergar a malha e o histórico do anterior."""
    from climasense.servicos import simulador

    simulador.limpar_cache()
    yield
    simulador.limpar_cache()
