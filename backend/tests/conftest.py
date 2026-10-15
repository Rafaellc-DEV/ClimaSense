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

from climasense.config import Configuracao
from climasense.infra.postgres import criar_engine, fabrica_sessoes

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
        c.execute(text("drop view if exists public.silver_vacinados"))
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


@pytest.fixture
def sessao(engine_teste):
    """Sessão com transação desfeita ao fim de cada teste (o banco volta limpo)."""
    conexao = engine_teste.connect()
    transacao = conexao.begin()
    s = fabrica_sessoes(engine_teste)(bind=conexao, join_transaction_mode="create_savepoint")
    try:
        yield s
    finally:
        s.close()
        transacao.rollback()
        conexao.close()
