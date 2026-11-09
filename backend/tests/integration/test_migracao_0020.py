"""0020: tabelas de hidrologia (rios e reservatórios); upgrade, downgrade e privilégios do papel da aplicação."""

import pytest
from alembic import command
from sqlalchemy import text

from tests.conftest import URL_TESTE, _alembic, precisa_postgres, recriar_banco

pytestmark = [precisa_postgres, pytest.mark.integracao]

SILVER = (
    "silver.rios_estacoes",
    "silver.rios_leituras",
    "silver.reservatorios",
    "silver.reservatorios_leituras",
    "silver.rio_referencia_territorio",
)
GOLD = ("gold.rio_situacao", "gold.reservatorio_situacao")
FONTES = ("apac-rios", "apac-reservatorios")


def _existe(engine, tabela: str) -> bool:
    with engine.connect() as c:
        return c.execute(text("select to_regclass(:t)"), {"t": tabela}).scalar() is not None


def _fontes(engine) -> set[str]:
    with engine.connect() as c:
        linhas = c.execute(text("select id from app.fontes where id in ('apac-rios', 'apac-reservatorios')"))
        return {r[0] for r in linhas}


def test_0020_cria_as_tabelas_e_o_downgrade_remove():
    engine = recriar_banco(URL_TESTE)
    try:
        assert all(_existe(engine, t) for t in SILVER + GOLD)
        assert _fontes(engine) == set(FONTES)
        with engine.connect() as c:
            implementadas = c.execute(
                text(
                    "select count(*) from app.fontes where id in ('apac-rios', 'apac-reservatorios') and implementada"
                )
            ).scalar()
            assert implementadas == 2
            # a referência bairro ↔ rio nasce vazia: nenhuma ligação é inferida
            assert c.execute(text("select count(*) from silver.rio_referencia_territorio")).scalar() == 0
        command.downgrade(_alembic(URL_TESTE), "0019")
        assert not any(_existe(engine, t) for t in SILVER + GOLD)
        assert _fontes(engine) == set()
        command.upgrade(_alembic(URL_TESTE), "head")
        assert all(_existe(engine, t) for t in SILVER + GOLD) and _fontes(engine) == set(FONTES)
    finally:
        engine.dispose()
        recriar_banco(URL_TESTE).dispose()


def test_0020_papel_da_aplicacao_so_le_as_tabelas_novas(engine_teste):
    with engine_teste.connect() as c:
        for tabela in SILVER + GOLD:
            privilegios = {
                p: c.execute(
                    text("select has_table_privilege('climasense_app', :t, :p)"), {"t": tabela, "p": p}
                ).scalar()
                for p in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE")
            }
            assert privilegios == {
                "SELECT": True,
                "INSERT": False,
                "UPDATE": False,
                "DELETE": False,
                "TRUNCATE": False,
            }, tabela


def test_0020_banco_recusa_limiares_fora_de_ordem_e_nivel_negativo(sessao):
    sessao.execute(
        text(
            "insert into silver.rios_estacoes (codigo, nome, lat, lon, fonte_id, atualizado_em) "
            "values ('T1', 'Teste', -8, -35, 'apac-rios', now())"
        )
    )
    sessao.execute(
        text(
            "insert into app.etl_execucoes (id, fonte_id, status) "
            "values ('00000000-0000-0000-0000-000000000001', 'apac-rios', 'sucesso')"
        )
    )
    base = (
        "insert into silver.rios_leituras (estacao_codigo, fonte, lida_em, nivel_cm, pre_alerta_cm, alerta_cm, "
        "enchente_cm, coletado_em, visto_em, execucao_id) values ('T1', 'apac', now(), {n}, {a}, {b}, {c}, now(), "
        "now(), '00000000-0000-0000-0000-000000000001')"
    )
    sessao.execute(text(base.format(n=10, a=250, b=300, c=400)))  # válido
    for n, a, b, c in ((-1, 250, 300, 400), (10, 300, 250, 400), (10, 250, "null", 400)):
        with pytest.raises(Exception, match="check"), sessao.begin_nested():
            sessao.execute(text(base.format(n=n, a=a, b=b, c=c)))
