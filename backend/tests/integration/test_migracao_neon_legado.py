"""A migração 0002 não pode apagar nem quebrar a tabela que o ETL antigo criou no Neon."""

import pytest
from alembic import command
from sqlalchemy import text

from tests.conftest import URL_TESTE, _alembic, precisa_postgres, recriar_banco

pytestmark = [precisa_postgres, pytest.mark.integracao]


def test_tabela_antiga_do_etl_e_preservada_com_os_dados():
    engine = recriar_banco(URL_TESTE)
    command.downgrade(_alembic(URL_TESTE), "0001")
    with engine.begin() as c:
        c.execute(text("create table public.silver_vacinados (idade integer, vacina text)"))
        c.execute(text("insert into public.silver_vacinados values (70, 'COMIRNATY (PFIZER)')"))
    command.upgrade(_alembic(URL_TESTE), "head")
    with engine.connect() as c:
        assert c.execute(text("select idade, vacina from public.silver_vacinados_legado_etl_avd")).all() == [
            (70, "COMIRNATY (PFIZER)")
        ]
        tipo = c.execute(
            text("select table_type from information_schema.tables where table_name = 'silver_vacinados'")
        ).scalar()
        assert tipo == "VIEW"
    with engine.begin() as c:
        c.execute(text("drop table public.silver_vacinados_legado_etl_avd"))
    recriar_banco(URL_TESTE).dispose()
    engine.dispose()
