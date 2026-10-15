"""Conexão com o Postgres (Neon na nuvem ou local) — T2.3."""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from climasense.config import Configuracao, obter_configuracao


def normalizar_url(url: str) -> str:
    """Aceita `postgres://` e `postgresql://` (formato do Neon) e usa o driver psycopg2 do ETL anterior."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://") :]
    return url


def criar_engine(url: str) -> Engine:
    return create_engine(
        normalizar_url(url),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        connect_args={"connect_timeout": 15},
    )


@lru_cache
def _engine_padrao(url: str) -> Engine:
    return criar_engine(url)


def engine_da_configuracao(config: Configuracao | None = None) -> Engine:
    config = config or obter_configuracao()
    return _engine_padrao(config.exigir("database_url"))


def fabrica_sessoes(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def obter_sessao() -> Iterator[Session]:
    """Dependência FastAPI: uma sessão por requisição, com commit explícito nos serviços."""
    sessao = fabrica_sessoes(engine_da_configuracao())()
    try:
        yield sessao
    finally:
        sessao.close()


def verificar(engine: Engine) -> bool:
    with engine.connect() as conexao:
        return conexao.execute(text("select 1")).scalar() == 1
