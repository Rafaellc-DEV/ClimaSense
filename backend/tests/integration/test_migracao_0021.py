"""0021: meteorologia observada e de modelo. Só tabelas novas e três fontes; o papel da aplicação só lê."""

import pytest
from alembic import command
from sqlalchemy import text

from tests.conftest import URL_TESTE, _alembic, precisa_postgres, recriar_banco

pytestmark = [precisa_postgres, pytest.mark.integracao]

SILVER = (
    "apac_chuva_passos",
    "apac_estacoes_cadastro",
    "solo_modelo_horario",
    "solo_modelo_diario",
    "apac_previsao_horaria",
    "apac_tendencia_chuva",
    "apac_radar",
)
GOLD = ("chuva_obs_hora_distrito", "chuva_obs_72h_distrito", "estacoes_chuva_status", "solo_modelo_distrito")
FONTES = ("open-meteo-solo", "open-meteo-temperatura", "apac-previsao")


def _existe(engine, tabela: str) -> bool:
    with engine.connect() as c:
        return c.execute(text("select to_regclass(:t)"), {"t": tabela}).scalar() is not None


def _tem(c, tabela: str, privilegio: str) -> bool:
    return c.execute(
        text("select has_table_privilege('climasense_app', :t, :p)"), {"t": tabela, "p": privilegio}
    ).scalar()


def _tabelas(engine):
    return [f"silver.{t}" for t in SILVER] + [f"gold.{t}" for t in GOLD]


def test_0021_cria_tabelas_e_fontes_e_o_downgrade_desfaz():
    engine = recriar_banco(URL_TESTE)
    try:
        assert all(_existe(engine, t) for t in _tabelas(engine))
        with engine.connect() as c:
            fontes = {
                r[0]: r[1:]
                for r in c.execute(
                    text("select id, tipo, implementada from app.fontes where id = any(:f)"),
                    {"f": list(FONTES)},
                )
            }
        assert fontes == {
            "open-meteo-solo": ("derivada", True),  # modelo, nunca "observada"
            "open-meteo-temperatura": ("prevista", True),
            "apac-previsao": ("prevista", True),
        }
        # downgrade e upgrade de novo (tabelas vazias, fontes de volta)
        command.downgrade(_alembic(URL_TESTE), "0019")
        assert not any(_existe(engine, t) for t in _tabelas(engine))
        with engine.connect() as c:
            assert (
                c.execute(
                    text("select count(*) from app.fontes where id = any(:f)"), {"f": list(FONTES)}
                ).scalar()
                == 0
            )
        command.upgrade(_alembic(URL_TESTE), "head")
        assert all(_existe(engine, t) for t in _tabelas(engine))
    finally:
        engine.dispose()
        recriar_banco(URL_TESTE).dispose()


def test_0021_papel_da_aplicacao_so_le_as_tabelas_novas():
    engine = recriar_banco(URL_TESTE)
    try:
        with engine.connect() as c:
            if not c.execute(text("select 1 from pg_roles where rolname = 'climasense_app'")).scalar():
                pytest.skip("o papel climasense_app não existe neste banco")
            for tabela in _tabelas(engine):
                for privilegio in ("INSERT", "UPDATE", "DELETE", "TRUNCATE"):
                    assert not _tem(c, tabela, privilegio), (tabela, privilegio)
                assert _tem(c, tabela, "SELECT"), tabela
    finally:
        engine.dispose()
        recriar_banco(URL_TESTE).dispose()


def test_0021_rejeita_valor_impossivel_no_banco():
    engine = recriar_banco(URL_TESTE)
    try:
        with engine.begin() as c:
            c.execute(
                text("insert into app.etl_execucoes (fonte_id, status) values ('open-meteo-solo', 'sucesso')")
            )
            eid = c.execute(text("select id from app.etl_execucoes order by inicio desc limit 1")).scalar()
            c.execute(
                text(
                    "insert into app.territorios (id, tipo, nome_oficial, nome_exibicao) values ('ds-teste', 'distrito', 'Teste', 'Teste') "
                    "on conflict do nothing"
                )
            )
        with pytest.raises(Exception, match="solo_modelo_horario"):  # umidade do solo fora de 0 a 1
            with engine.begin() as c:
                c.execute(
                    text(
                        "insert into silver.solo_modelo_horario (territorio_id, camada, observado_em, valor_m3m3, "
                        "emitido_em, coletado_em, execucao_id) values ('ds-teste', '0_7cm', now(), 1.7, now(), now(), :e)"
                    ),
                    {"e": eid},
                )
        with pytest.raises(Exception, match="apac_chuva_passos"):  # chuva negativa não existe
            with engine.begin() as c:
                c.execute(
                    text(
                        "insert into silver.estacoes (id, fonte_id, codigo_fonte, nome, lat, lon, ativa) "
                        "values ('apac-x', 'apac-chuva', 'x', 'x', -8, -35, true) on conflict do nothing"
                    )
                )
                c.execute(
                    text(
                        "insert into silver.apac_chuva_passos (estacao_id, lida_em, valor_mm, coletado_em, visto_em, "
                        "execucao_id) values ('apac-x', now(), -1, now(), now(), :e)"
                    ),
                    {"e": eid},
                )
    finally:
        engine.dispose()
        recriar_banco(URL_TESTE).dispose()
