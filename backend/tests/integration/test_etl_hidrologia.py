"""Hidrologia de ponta a ponta no Postgres de teste, com as respostas REAIS gravadas em 06/11/2026: APAC (e ANA) →
bronze acumulativa → silver → gold reproduzível. Tudo roda dentro de uma transação desfeita no fim."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import mongomock
import pytest
from sqlalchemy import text

from climasense.etl import execucao, gold
from climasense.etl.conectores import apac_reservatorios, apac_rios
from climasense.etl.conectores.base import ExecucaoCtx
from tests.conftest import configuracao_teste, precisa_postgres
from tests.integration.test_etl_chuva import EngineNaTransacao
from tests.unit.etl.test_conectores_chuva import Http, Resposta, _json
from tests.unit.etl.test_conectores_hidrologia import _rotas

pytestmark = [precisa_postgres, pytest.mark.integracao]
AGORA = datetime(2026, 11, 7, 1, 58, tzinfo=UTC)  # 22:58 de 06/11 no Recife


HIDROLOGIA = ("gold.rio_situacao", "gold.reservatorio_situacao")


@pytest.fixture
def ambiente(engine_teste, monkeypatch):
    # verifica só a gold desta frente (as demais dependem de migrações de outras frentes)
    monkeypatch.setattr(gold, "VERIFICADAS", {t: q for t, q in gold.VERIFICADAS.items() if t in HIDROLOGIA})
    conexao = engine_teste.connect()
    transacao = conexao.begin()
    try:
        yield EngineNaTransacao(conexao), mongomock.MongoClient(), configuracao_teste()
    finally:
        transacao.rollback()
        conexao.close()


def rodar(engine, mongo, config, conector, agora=AGORA, modo=None, limite=None):
    eid = execucao.iniciar(engine, conector.id)
    r = conector.executar(ExecucaoCtx(eid, config, mongo, engine, agora, limite, modo))
    execucao.concluir(engine, eid, lidos=r.lidos, gravados=r.gravados)
    return r


def rios(engine, mongo, config, **kw):
    return rodar(engine, mongo, config, apac_rios.ConectorApacRios(http=Http(_rotas())), **kw)


def situacao(c):
    campos = "classe, motivo, nivel_cm, pre_alerta_cm, alerta_cm, enchente_cm, fonte_leitura, fontes, idade_min, desatualizada"
    return {
        r[0]: tuple(r[1:])
        for r in c.execute(text(f"select estacao_codigo, {campos} from gold.rio_situacao"))  # noqa: S608
    }


def test_rios_viram_gold_reproduzivel_com_classe_hora_e_idade(ambiente):
    engine, mongo, config = ambiente
    r = rios(engine, mongo, config)
    assert (r.lidos, r.gravados) == (8 + 8 + 1, 6 * 4 + 4)  # cadastro + históricos + ANA; leituras novas
    assert rios(engine, mongo, config).gravados == 0  # a mesma leitura não duplica
    assert mongo["bronze"]["apac_rios"].count_documents({}) == 34  # bronze acumulativa (RN-09)
    c = engine.c
    assert gold.verificar(c) == dict.fromkeys(HIDROLOGIA, 0)
    s = situacao(c)
    assert len(s) == 8
    # São Lourenço da Mata: a ANA (15:15 de 06/11) é mais fresca que a APAC (16:15 de 05/11); limiares são da APAC
    assert s["39187800"] == (
        "abaixo_pre_alerta",
        None,
        177.0,
        250.0,
        300.0,
        400.0,
        "ana",
        ["ana", "apac"],
        463,
        True,
    )
    # leitura com 24 h de idade (APAC atrasada): Dados insuficientes, nunca "abaixo do pré-alerta"
    assert s["39150010"][:2] == ("dados_insuficientes", "leitura_antiga") and s["39150010"][8] > 720
    # lista vazia na APAC: sem leitura, sem nível (nunca 0)
    for cod in ("39170000", "39189560"):
        assert s[cod][:3] == ("dados_insuficientes", "sem_leitura", None) and s[cod][8] is None
    assert (
        c.execute(
            text("select inclui_recife from gold.rio_situacao where estacao_codigo = '39187800'")
        ).scalar()
        is True
    )
    assert c.execute(text("select count(*) from silver.rio_referencia_territorio")).scalar() == 0


def test_gold_do_rio_segue_os_mesmos_limiares_que_o_python(ambiente):
    engine, mongo, config = ambiente
    rios(engine, mongo, config)
    c = engine.c
    for nivel in (0, 100, 249.9, 250, 299.9, 300, 399.9, 400, 650):
        c.execute(
            text(
                "update silver.rios_leituras set nivel_cm = :n where estacao_codigo = '39187800' and fonte = 'ana' "
                "and lida_em = (select max(lida_em) from silver.rios_leituras where estacao_codigo = '39187800' "
                "and fonte = 'ana')"
            ),
            {"n": nivel},
        )
        gold.recalcular(c, gold.TABELAS_RIOS)
        classe = situacao(c)["39187800"][0]
        assert classe == apac_rios.classificar_nivel(nivel, 250, 300, 400), nivel
    assert classe == "enchente"


def test_estacao_sem_limiares_validos_fica_sem_classe(ambiente):
    engine, mongo, config = ambiente
    rios(engine, mongo, config)
    c = engine.c
    c.execute(
        text(
            "update silver.rios_leituras set pre_alerta_cm = null, alerta_cm = null, enchente_cm = null "
            "where estacao_codigo = '39187800'"
        )
    )
    gold.recalcular(c, gold.TABELAS_RIOS)
    assert situacao(c)["39187800"][:2] == ("dados_insuficientes", "sem_limiares")


def test_rios_amostra_so_com_parte_das_estacoes_fica_rotulada_na_bronze(ambiente):
    engine, mongo, config = ambiente
    rios(engine, mongo, config, limite=2)
    docs = list(mongo["bronze"]["apac_rios"].find({"_origem": "apac_historico"}))
    assert len(docs) == 2 and all(d["amostra"] and d["n_estacoes"] == 2 for d in docs)
    assert len(situacao(engine.c)) == 2  # as demais estações nem entram: ausência não vira classe


def test_reservatorios_viram_gold_e_leitura_antiga_vira_dados_insuficientes(ambiente):
    engine, mongo, config = ambiente
    http = Http({"reservatorio": Resposta(_json("apac_reservatorio_capibaribe_2026-11-06.json"))})
    r = rodar(engine, mongo, config, apac_reservatorios.ConectorApacReservatorios(http=http))
    assert (r.lidos, r.gravados) == (14, 4)
    assert mongo["bronze"]["apac_reservatorios"].count_documents({}) == 14
    c = engine.c
    assert gold.verificar(c) == dict.fromkeys(HIDROLOGIA, 0)
    linhas = {
        r[0]: tuple(r[1:])
        for r in c.execute(
            text(
                "select codigo_estacao, nome, situacao, motivo, volume_pct, idade_dias from gold.reservatorio_situacao"
            )
        )
    }
    assert linhas[39175000] == ("Tapacurá", "entre_80_e_100", None, 95.36, 0)
    assert linhas[39187900][1:] == ("vertendo", None, 100.2, 0)
    assert linhas[39151000][1] == "entre_30_e_80" and linhas[39145550][1] == "entre_10_e_30"
    # cinco dias depois, com a mesma resposta (leituras de 06/11): passou de 3 dias
    rodar(
        engine,
        mongo,
        config,
        apac_reservatorios.ConectorApacReservatorios(http=http),
        agora=AGORA + timedelta(days=5),
    )
    velhas = c.execute(text("select distinct situacao, motivo from gold.reservatorio_situacao")).all()
    assert velhas == [("dados_insuficientes", "leitura_antiga")]
