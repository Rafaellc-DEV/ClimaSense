"""Ambiente do Alembic: a URL do dono do banco vem do .env (DATABASE_URL_MIGRACOES) ou de `-x url=...` (testes)."""

from alembic import context
from sqlalchemy import pool

from climasense.config import obter_configuracao
from climasense.infra.postgres import criar_engine, url_do_dono


def _url() -> str:
    x = context.get_x_argument(as_dictionary=True)
    return x.get("url") or url_do_dono(obter_configuracao())


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
