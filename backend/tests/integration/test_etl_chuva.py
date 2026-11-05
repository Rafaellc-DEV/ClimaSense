"""Foco em chuvas de ponta a ponta no Postgres de teste, com as respostas REAIS gravadas (tests/unit/etl/fixtures):
APAC → silver/gold → `estagios.chuva_24h`; alertas → silver → `estagios.alertas_oficiais`; abrigos dos Dados
Abertos e do COP → `app.abrigos` sem sobrescrever a equipe → `/publico/abrigos`.

Tudo roda dentro de uma transação desfeita no fim (o histórico de abrigos só aceita inclusões e não pode ser
limpo depois)."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import mongomock
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from climasense.etl import execucao, gold
from climasense.etl.conectores.abrigos import ConectorRecifeAbrigos
from climasense.etl.conectores.alertas import ConectorAlertasOficiais
from climasense.etl.conectores.apac import ConectorApacChuva
from climasense.etl.conectores.base import ExecucaoCtx
from climasense.servicos import abrigos as servico_abrigos
from climasense.servicos import estagios
from climasense.territorio import carga
from tests.conftest import configuracao_teste, precisa_postgres
from tests.integration.apoio import Relogio, cliente, criar_conta
from tests.unit.etl.test_conectores_chuva import Http, Resposta, _http_abrigos, _http_alertas, _json

pytestmark = [precisa_postgres, pytest.mark.integracao]
AGORA = datetime(2026, 11, 5, 2, 0, tzinfo=UTC)


class EngineNaTransacao:
    """Faz `engine.begin()`/`connect()` dos conectores virarem savepoints de uma transação externa."""

    def __init__(self, conexao) -> None:
        self.c = conexao

    @contextmanager
    def begin(self):
        with self.c.begin_nested():
            yield self.c

    @contextmanager
    def connect(self):
        yield self.c


@pytest.fixture
def ambiente(engine_teste):
    conexao = engine_teste.connect()
    transacao = conexao.begin()
    db = Session(bind=conexao, join_transaction_mode="create_savepoint")
    carga.sincronizar_territorios(db, carga.geo_local())
    try:
        yield EngineNaTransacao(conexao), mongomock.MongoClient(), configuracao_teste(), db
    finally:
        db.close()
        transacao.rollback()
        conexao.close()


def rodar(engine, mongo, config, conector, modo=None, agora=AGORA, limite=None):
    eid = execucao.iniciar(engine, conector.id)
    r = conector.executar(ExecucaoCtx(eid, config, mongo, engine, agora, limite, modo))
    execucao.concluir(engine, eid, lidos=r.lidos, gravados=r.gravados)
    return r


def test_apac_tempo_real_e_historico_viram_gold_reproduzivel_e_chuva_24h_prefere_a_apac(ambiente):
    engine, mongo, config, db = ambiente
    http = Http({"precipitacao_acumulada": Resposta(_json("apac_precipitacao_acumulada_2026-11-04.json"))})
    r = rodar(engine, mongo, config, ConectorApacChuva(http=http))
    assert (r.lidos, r.gravados) == (19, 19 * 9)
    assert (
        rodar(engine, mongo, config, ConectorApacChuva(http=http)).gravados == 0
    )  # mesma leitura não duplica
    assert mongo["bronze"]["apac_chuva"].count_documents({}) == 38  # bronze acumulativa
    historico = Http({"historico_pluviometrico_mensal": Resposta(_json("apac_historico_2026-10.json"))})
    rodar(engine, mongo, config, ConectorApacChuva(http=historico), modo="historico", limite=1)
    c = engine.c
    assert gold.verificar(c) == {t: 0 for t in gold.VERIFICADAS}
    ibura = c.execute(
        text(
            "select n_atualizadas, herdado_de from gold.chuva_apac_agora where territorio_id = 'bairro-cohab'"
        )
    ).one()
    # a estação do Ibura (única do DS VIII) leu pela última vez em 30/10: desatualizada, não conta como 0 mm;
    # bairro e distrito herdam do Recife, marcados (RN-07)
    assert ibura == (16, "recife")
    assert engine.c.execute(
        text("select n_estacoes, herdado_de from gold.chuva_apac_agora where territorio_id = 'ds-8'")
    ).one() == (19, "recife")
    ds2 = c.execute(
        text(
            "select chuva_24h_max_mm, n_estacoes, herdado_de from gold.chuva_apac_agora where territorio_id = 'ds-2'"
        )
    ).one()
    assert ds2 == (0.2, 4, None)  # Campina do Barreto: 0,2 mm em 24 h
    assert (
        c.execute(text("select count(*) from gold.chuva_apac_diaria where territorio_id = 'recife'")).scalar()
        == 31
    )
    assert estagios.chuva_24h(db, "ds-2", AGORA) == (0.2, ["apac-chuva"])
    assert estagios.chuva_24h(db, "ds-2", AGORA + timedelta(hours=5))[1] != ["apac-chuva"]  # leitura velha


def test_alertas_oficiais_na_silver_aparecem_nos_estagios(ambiente):
    engine, mongo, config, db = ambiente
    inmet = _json("inmet_avisos_ativos_2026-11-04.json")
    aviso = next(
        a for a in inmet["hoje"] + inmet["futuro"] if ",26" in a["geocodes"] or a["geocodes"].startswith("26")
    )
    aviso["geocodes"] += ",2611606"  # ALTERADO: o aviso real de PE passa a incluir o Recife
    aviso["fim"] = "2026-11-06 23:59"
    http = _http_alertas(inmet=inmet)
    assert rodar(engine, mongo, config, ConectorAlertasOficiais(http=http)).gravados == 1
    assert (
        rodar(engine, mongo, config, ConectorAlertasOficiais(http=http)).gravados == 1
    )  # upsert, sem duplicar
    assert engine.c.execute(text("select count(*) from silver.alertas_oficiais")).scalar() == 1
    lista = estagios.alertas_oficiais("ds-4", db, AGORA)
    assert len(lista) == 1 and lista[0]["origem"] == "inmet" and lista[0]["criterio_geo"] == "geocode"
    assert estagios.alertas_oficiais("ds-4", db, datetime(2026, 11, 8, tzinfo=UTC)) == []  # venceu
    assert estagios.alertas_oficiais("ds-4") == []


def test_abrigos_nao_sobrescrevem_a_equipe_o_cop_abre_e_fecha_e_a_landing_nao_expoe_pessoas(
    ambiente, tmp_path
):
    engine, mongo, config, db = ambiente
    sem_curado = tmp_path / "nao-existe.csv"
    r = rodar(engine, mongo, config, ConectorRecifeAbrigos(http=_http_abrigos(), arquivo_curado=sem_curado))
    assert r.gravados == 17
    autor = criar_conta(db, "equipe-abrigos@recife.pe.gov.br", ["analista"], nome="Servidora Fulana")
    alvo = db.execute(
        text("select id from app.abrigos where codigo_fonte = 'ckan:escola-municipal-dina-de-oliveira'")
    ).scalar_one()
    servico_abrigos.atualizar(db, alvo, {"aberto": True, "pessoas_abrigadas": 12}, autor, None, AGORA)
    rodar(engine, mongo, config, ConectorRecifeAbrigos(http=_http_abrigos(), arquivo_curado=sem_curado))
    c = engine.c
    assert c.execute(
        text("select aberto, pessoas_abrigadas from app.abrigos where id = :i"), {"i": alvo}
    ).one() == (
        True,
        12,
    )  # a recarga não mexe no que a equipe registrou
    assert c.execute(text("select count(*) from app.abrigos")).scalar() == 17

    feicao = {
        "attributes": {
            "globalid": "{1}",
            "no_entidade": "Escola Municipal Casarão do Barbalho",
            "latitude": -8.028799,
            "longitude": -34.934646,
            "status": "ATIVO",
            "qtd_vagas_estimadas_quadra": 80,
        }
    }
    depois = AGORA + timedelta(minutes=15)
    rodar(
        engine,
        mongo,
        config,
        ConectorRecifeAbrigos(http=_http_abrigos({"features": [feicao]})),
        "ativos",
        depois,
    )
    casarao = "select aberto, status_origem from app.abrigos where codigo_fonte = 'ckan:escola-municipal-casarao-do-barbalho'"
    assert c.execute(text(casarao)).one() == (True, "cop")
    assert c.execute(text("select count(*) from app.abrigos")).scalar() == 17  # casou com o cadastrado

    relogio = Relogio()
    relogio.agora = depois
    publico = cliente(db, relogio).get("/api/v1/publico/abrigos")
    assert publico.status_code == 200
    corpo = publico.json()
    assert "0800 081 3400" in corpo["aviso"] and "199" in corpo["aviso"]
    casa = next(i for i in corpo["itens"] if i["nome"].startswith("Escola Municipal Casar"))
    assert (casa["aberto"], casa["aberto_fonte"], casa["capacidade"]) == (True, "cop", 80)
    assert casa["bairro_nome"] and casa["fonte_url"]
    dina = next(i for i in corpo["itens"] if i["id"] == str(alvo))
    assert (dina["aberto"], dina["aberto_fonte"]) == (True, "equipe")
    nunca = [i for i in corpo["itens"] if i["aberto_fonte"] is None]
    assert len(nunca) == 15 and all(i["aberto"] is None for i in nunca)  # nunca informado ≠ fechado
    assert "Servidora Fulana" not in publico.text and "pessoas_abrigadas" not in publico.text

    rodar(
        engine,
        mongo,
        config,
        ConectorRecifeAbrigos(http=_http_abrigos()),
        "ativos",
        depois + timedelta(minutes=15),
    )
    assert c.execute(text(casarao)).one() == (False, "cop")  # saiu do feed: o COP fechou
    assert c.execute(text("select aberto from app.abrigos where id = :i"), {"i": alvo}).scalar() is True
    assert (
        c.execute(text("select count(*) from app.abrigo_atualizacoes where autor_id is null")).scalar() == 2
    )
