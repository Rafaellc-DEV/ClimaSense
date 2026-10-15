"""Ambiente do Alembic: a URL do banco vem da configuração (.env) ou de `-x url=...` (usado nos testes)."""

from alembic import context
from sqlalchemy import pool

from climasense.config import obter_configuracao
from climasense.infra.postgres import criar_engine


def _url() -> str:
    x = context.get_x_argument(as_dictionary=True)
    return x.get("url") or obter_configuracao().exigir("database_url")


def run_migrations_offline() -> None:
    context.configure(
        url=_url(), literal_binds=True, dialect_opts={"paramstyle": "named"}, version_table_schema="public"
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = criar_engine(_url())
    engine.pool = pool.NullPool(engine.pool._creator)  # sem pool nas migrações
    with engine.connect() as conexao:
        context.configure(connection=conexao, version_table_schema="public")
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
