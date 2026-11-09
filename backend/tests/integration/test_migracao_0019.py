"""0019: abrigos saem do banco e a exclusão de ações fica possível; upgrade e downgrade funcionam."""

import pytest
from alembic import command
from sqlalchemy import text

from tests.conftest import URL_TESTE, _alembic, precisa_postgres, recriar_banco

pytestmark = [precisa_postgres, pytest.mark.integracao]

TABELAS = ("app.abrigos", "app.abrigo_atualizacoes")


def _existe(engine, tabela: str) -> bool:
    with engine.connect() as c:
        return c.execute(text("select to_regclass(:t)"), {"t": tabela}).scalar() is not None


def test_0019_remove_as_tabelas_e_o_downgrade_recria_vazias():
    engine = recriar_banco(URL_TESTE)
    try:
        assert not any(_existe(engine, t) for t in TABELAS)
        with engine.connect() as c:
            assert (
                c.execute(text("select count(*) from app.fontes where id like 'recife-abrigos%'")).scalar()
                == 0
            )
            fk = c.execute(
                text("select count(*) from pg_constraint where conname = 'acao_eventos_acao_id_fkey'")
            ).scalar()
            assert fk == 0
        command.downgrade(_alembic(URL_TESTE), "0018")
        assert all(_existe(engine, t) for t in TABELAS)
        command.upgrade(_alembic(URL_TESTE), "head")
        assert not any(_existe(engine, t) for t in TABELAS)
    finally:
        engine.dispose()
        recriar_banco(URL_TESTE).dispose()
