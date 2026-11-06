"""O papel `climasense_app` faz o que a API precisa e nada além (RNF-01, RNF-12, ADR 0014)."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from tests.conftest import precisa_postgres

pytestmark = [precisa_postgres, pytest.mark.integracao]

SOMENTE_INCLUSAO = (
    "auditoria",
    "estagio_parametros",
    "estagio_declaracoes",
    "abrigo_atualizacoes",
    "acao_eventos",
    "liberacoes_login",
)


def _negado(conexao, sql: str) -> None:
    with pytest.raises((ProgrammingError, DBAPIError)) as erro, conexao.begin_nested():
        conexao.execute(text(sql))
    assert "permission denied" in str(erro.value).lower() or "must be owner" in str(erro.value).lower()


@pytest.fixture
def app(engine_app):
    conexao = engine_app.connect()
    transacao = conexao.begin()
    try:
        yield conexao
    finally:
        transacao.rollback()
        conexao.close()


def test_papel_nao_tem_poderes_de_dono(engine_teste):
    with engine_teste.connect() as c:
        r = (
            c.execute(
                text(
                    "select rolsuper, rolcreatedb, rolcreaterole, rolcanlogin, rolbypassrls from pg_roles "
                    "where rolname = 'climasense_app'"
                )
            )
            .mappings()
            .one()
        )
        assert dict(r) == {
            "rolsuper": False,
            "rolcreatedb": False,
            "rolcreaterole": False,
            "rolcanlogin": True,
            "rolbypassrls": False,
        }
        donas = c.execute(
            text(
                "select count(*) from pg_class c join pg_roles r on r.oid = c.relowner "
                "where r.rolname = 'climasense_app'"
            )
        ).scalar()
        assert donas == 0


def test_conecta_como_o_papel_da_aplicacao(app):
    assert app.execute(text("select current_user")).scalar() == "climasense_app"


def test_auditoria_so_aceita_inclusao(app):
    app.execute(text("insert into app.auditoria (acao, alvo_tipo, alvo_id) values ('teste_papel', 't', '1')"))
    assert app.execute(text("select count(*) from app.auditoria where acao = 'teste_papel'")).scalar() == 1
    _negado(app, "update app.auditoria set acao = 'x'")
    _negado(app, "delete from app.auditoria")
    _negado(app, "truncate app.auditoria")


@pytest.mark.parametrize("tabela", SOMENTE_INCLUSAO)
def test_privilegios_das_tabelas_somente_inclusao(engine_teste, tabela):
    with engine_teste.connect() as c:
        tem = lambda priv: c.execute(  # noqa: E731
            text("select has_table_privilege('climasense_app', :t, :p)"), {"t": f"app.{tabela}", "p": priv}
        ).scalar()
        assert tem("SELECT") and tem("INSERT")
        assert not tem("UPDATE") and not tem("DELETE") and not tem("TRUNCATE")


def test_nao_faz_ddl(app):
    _negado(app, "create table public.intrusa (x int)")
    _negado(app, "create table app.intrusa (x int)")
    _negado(app, "create schema intrusa")
    _negado(app, "drop table app.usuarios")
    _negado(app, "alter table app.usuarios add column x int")
    _negado(app, "create role intrusa")
    _negado(app, "truncate app.usuarios")


def test_nao_escreve_em_silver_e_gold_exceto_previsoes(app):
    _negado(app, "delete from silver.observacoes")
    _negado(app, "insert into gold.chuva_diaria default values")
    _negado(app, "update silver.estacoes set id = id")
    _negado(app, "truncate gold.chuva_diaria")
    assert app.execute(text("select count(*) from gold.chuva_diaria")).scalar() >= 0
    assert app.execute(text("select has_table_privilege('silver.previsoes_emitidas', 'INSERT')")).scalar()
    assert not app.execute(text("select has_table_privilege('silver.previsoes_emitidas', 'UPDATE')")).scalar()


def test_faz_o_que_a_api_precisa(app):
    app.execute(
        text(
            "insert into app.usuarios (nome, email, senha_hash, papeis) values ('Papel', 'papel@teste.dev', 'x', '{analista}')"
        )
    )
    app.execute(text("update app.usuarios set nome = 'Papel 2' where email = 'papel@teste.dev'"))
    app.execute(text("delete from app.sessoes"))
    app.execute(text("update app.fontes set min_observacoes = min_observacoes"))
    assert app.execute(text("select count(*) from app.fontes")).scalar() > 0
    assert app.execute(text("select count(*) from public.alembic_version")).scalar() == 1


def test_comando_criar_papel_app_define_senha_e_conecta(engine_teste, tmp_path):
    from sqlalchemy.engine import make_url

    from climasense.admin import definir_senha_do_papel_app, gravar_no_env
    from climasense.infra.postgres import criar_engine
    from tests.conftest import URL_TESTE

    url_app, url_dono = definir_senha_do_papel_app(URL_TESTE)
    assert make_url(url_app).username == "climasense_app"
    assert make_url(url_dono).username == make_url(URL_TESTE).username
    engine = criar_engine(url_app)
    try:
        with engine.connect() as c:
            assert c.execute(text("select current_user")).scalar() == "climasense_app"
    finally:
        engine.dispose()
    env = tmp_path / ".env"
    gravar_no_env(env, {"DATABASE_URL": url_app, "DATABASE_URL_MIGRACOES": url_dono})
    assert "DATABASE_URL_MIGRACOES=" in env.read_text()
