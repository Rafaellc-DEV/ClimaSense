"""SAMU, SISAGUA e Atlas no Postgres de teste (migração 0023): silver, gold reproduzível e privilégios.

Respostas reais gravadas (tests/unit/etl/fixtures); só o banco local de teste. Cada teste roda numa transação desfeita.
"""

from __future__ import annotations

import mongomock
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.etl import execucao, gold
from climasense.etl.conectores.atlas import ConectorAtlasDesastres
from climasense.etl.conectores.base import ExecucaoCtx
from climasense.etl.conectores.samu import ConectorSamuRecife
from climasense.etl.conectores.sisagua import ConectorSisagua
from climasense.territorio import carga
from tests.conftest import configuracao_teste, precisa_postgres
from tests.integration.test_etl_chuva import AGORA, EngineNaTransacao
from tests.unit.etl.test_conectores_saude_historico import _http_atlas, _http_samu, _servir, _sisagua

pytestmark = [precisa_postgres, pytest.mark.integracao]


@pytest.fixture
def ambiente(engine_teste):
    conexao = engine_teste.connect()
    transacao = conexao.begin()
    db = Session(bind=conexao, join_transaction_mode="create_savepoint")
    carga.sincronizar_territorios(db, carga.geo_local())
    try:
        yield EngineNaTransacao(conexao), mongomock.MongoClient(), configuracao_teste()
    finally:
        db.close()
        transacao.rollback()
        conexao.close()


def rodar(engine, mongo, config, conector):
    eid = execucao.iniciar(engine, conector.id)
    r = conector.executar(ExecucaoCtx(eid, config, mongo, engine, AGORA, None, None))
    execucao.concluir(engine, eid, lidos=r.lidos, gravados=r.gravados)
    return r


def test_migracao_registra_as_tres_fontes_como_implementadas(ambiente):
    engine, _, _ = ambiente
    linhas = engine.c.execute(
        text(
            "select id, implementada, licenca, limite_desatualizacao_h from app.fontes "
            "where id in ('samu-recife', 'sisagua', 'atlas-desastres') order by id"
        )
    ).all()
    assert linhas == [
        ("atlas-desastres", True, None, 13140),
        ("samu-recife", True, "ODbL", 1440),
        ("sisagua", True, None, 192),
    ]


def test_samu_silver_e_gold_guardam_contagem_inteira_e_nenhuma_coluna_individual(ambiente):
    engine, mongo, config = ambiente
    http = _http_samu({2025: "samu_2025_amostra.csv", 2026: "samu_2026_amostra.csv"})
    r = rodar(engine, mongo, config, ConectorSamuRecife(http=http))
    c = engine.c
    assert r.gravados > 0 and r.descartados >= 3  # chamados de outros municípios da regulação
    colunas = {
        x[0]
        for x in c.execute(
            text(
                "select column_name from information_schema.columns "
                "where table_schema in ('silver', 'gold') and table_name = 'samu_demanda_semana'"
            )
        )
    }
    assert not colunas & {"endereco", "sexo", "idade", "hora_minuto", "origem_chamado", "motivo_desfecho"}
    # município soma tudo; a SE 53/2025 junta os dois arquivos anuais
    total = c.execute(
        text(
            "select chamados, nivel, incompleta from gold.samu_demanda_semana "
            "where territorio_id = 'recife' and inicio = '2025-12-28' and grupo = 'total'"
        )
    ).one()
    assert total[1] == "municipio" and total[0] > 0
    # a gold guarda a contagem de 1 a 4 (a supressão é da API): existe célula pequena não nula
    assert (
        c.execute(
            text("select count(*) from gold.samu_demanda_semana where chamados between 1 and 4")
        ).scalar()
        > 0
    )
    # bairro e distrito: Boa Viagem e o distrito dele; o distrito soma os bairros oficiais dele
    bairro = c.execute(
        text(
            "select sum(chamados) from gold.samu_demanda_semana "
            "where territorio_id = 'bairro-boa-viagem' and grupo = 'total'"
        )
    ).scalar()
    distrito_id = c.execute(
        text("select pai_id from app.territorios where id = 'bairro-boa-viagem'")
    ).scalar()
    distrito = c.execute(
        text(
            "select sum(chamados) from gold.samu_demanda_semana where territorio_id = :d and grupo = 'total'"
        ),
        {"d": distrito_id},
    ).scalar()
    assert bairro and distrito >= bairro
    assert gold.verificar(c)["gold.samu_demanda_semana"] == 0
    # carga repetida troca a série (arquivos republicados inteiros), sem duplicar
    antes = c.execute(text("select count(*) from silver.samu_demanda_semana")).scalar()
    rodar(engine, mongo, config, ConectorSamuRecife(http=http))
    assert c.execute(text("select count(*) from silver.samu_demanda_semana")).scalar() == antes
    assert (
        mongo["bronze"]["samu_recife"].count_documents({"tipo": "arquivo"}) == 4
    )  # bronze acumulativa (RN-09)


def test_sisagua_silver_e_gold_com_contagens_por_bairro_distrito_e_municipio(ambiente):
    engine, mongo, config = ambiente
    r = rodar(engine, mongo, config, ConectorSisagua(http=_servir({2026: _sisagua()}, 1000)))
    c = engine.c
    assert r.gravados > 0
    assert gold.verificar(c)["gold.agua_vigilancia_semana"] == 0
    municipio = c.execute(
        text(
            "select sum(analises_ecoli), sum(ecoli_presente), sum(analises_cloro) from gold.agua_vigilancia_semana "
            "where nivel = 'municipio'"
        )
    ).one()
    esperado_ecoli = sum(x["parametro"] == "Escherichia coli" for x in _sisagua())
    assert municipio[0] == esperado_ecoli and municipio[1] >= 3
    niveis = {x[0] for x in c.execute(text("select distinct nivel from gold.agua_vigilancia_semana"))}
    assert niveis == {"bairro", "distrito", "municipio"}
    # sem coleta na semana = sem linha (nunca "água boa")
    assert (
        c.execute(
            text(
                "select count(*) from gold.agua_vigilancia_semana "
                "where analises_ecoli = 0 and analises_cloro = 0"
            )
        ).scalar()
        == 0
    )


def test_atlas_silver_e_gold_trazem_os_16_eventos_do_recife(ambiente):
    engine, mongo, config = ambiente
    r = rodar(engine, mongo, config, ConectorAtlasDesastres(http=_http_atlas()))
    c = engine.c
    assert (r.lidos, r.gravados, r.descartados) == (17, 16, 0)  # 1 arquivo + 16 eventos
    assert gold.verificar(c)["gold.desastres_historico"] == 0
    e = c.execute(
        text(
            "select mortos, desabrigados, danos_materiais_rs, status, chuva_relacionada, consolidado_em "
            "from gold.desastres_historico where data_evento = '2022-05-29'"
        )
    ).one()
    assert (e[0], e[1], float(e[2]), e[3], e[4], str(e[5])) == (
        43,
        3874,
        61664230.93,
        "Reconhecido",
        True,
        "2026-08-06",
    )
    assert (
        c.execute(text("select count(*) from gold.desastres_historico where not chuva_relacionada")).scalar()
        == 3
    )


def test_papel_da_aplicacao_so_le_as_tabelas_novas(engine_teste):
    for esquema, tabela in (
        ("silver", "samu_demanda_semana"),
        ("silver", "agua_vigilancia_semana"),
        ("silver", "desastres_atlas"),
        ("gold", "samu_demanda_semana"),
        ("gold", "agua_vigilancia_semana"),
        ("gold", "desastres_historico"),
    ):
        with engine_teste.connect() as c:
            privilegios = {
                p: c.execute(
                    text("select has_table_privilege('climasense_app', :t, :p)"),
                    {"t": f"{esquema}.{tabela}", "p": p},
                ).scalar()
                for p in ("select", "insert", "update", "delete", "truncate")
            }
        assert privilegios == {
            "select": True,
            "insert": False,
            "update": False,
            "delete": False,
            "truncate": False,
        }
