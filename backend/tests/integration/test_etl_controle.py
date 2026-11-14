"""Controle real de concorrência, falhas e repetição de trabalho no Postgres descartável."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from sqlalchemy import text

from climasense.etl import execucao
from climasense.etl.conectores.base import ResultadoExecucao
from tests.conftest import configuracao_teste, precisa_postgres

pytestmark = [precisa_postgres, pytest.mark.integracao]


def test_construtor_falha_e_mongo_falha_sao_encerrados(engine_teste, monkeypatch):
    from climasense.infra import postgres

    def quebrar(*args):
        raise ConnectionError("URI-com-segredo-nao-publicar")

    fonte = "open-meteo-previsao"
    monkeypatch.setitem(execucao.CONECTORES, fonte, quebrar)
    eid = execucao.iniciar(engine_teste, fonte)
    r = execucao.executar(engine_teste, None, configuracao_teste(), fonte, eid)
    assert r["status"] == "falha" and "segredo" not in r["erro"]
    monkeypatch.setattr(postgres, "engine_do_dono", lambda c: engine_teste)
    monkeypatch.setattr(postgres, "engine_da_configuracao", lambda c: engine_teste)
    eid = execucao.iniciar(engine_teste, fonte)
    execucao.executar_preparado(configuracao_teste(), fonte, eid, obter_mongo=quebrar)
    with engine_teste.connect() as c:
        status, fim, erro = c.execute(
            text("select status,fim,erro from app.etl_execucoes where id=:i"), {"i": eid}
        ).one()
        assert status == "falha" and fim and "segredo" not in erro


def test_trava_entre_conexoes_e_repeticao_nao_reexecuta_conector(engine_teste):
    pronto, liberar = Event(), Event()
    chamadas = []

    class Lento:
        def executar(self, ctx):
            chamadas.append(ctx.execucao_id)
            pronto.set()
            assert liberar.wait(10)
            return ResultadoExecucao(lidos=2, gravados=2)

    fonte = "open-meteo-previsao"
    eid = execucao.iniciar(engine_teste, fonte)
    with ThreadPoolExecutor(max_workers=1) as pool:
        f = pool.submit(
            execucao.executar, engine_teste, None, configuracao_teste(), fonte, eid, conector=Lento()
        )
        try:
            assert pronto.wait(10)
            repetida = execucao.executar(
                engine_teste, None, configuracao_teste(), fonte, eid, conector=Lento()
            )
            assert repetida["status"] == "em_andamento" and chamadas == [eid]
            with pytest.raises(execucao.ExecucaoEmAndamento):
                execucao.iniciar(engine_teste, fonte)
            outro = execucao.iniciar(engine_teste, "open-meteo-mare")
            r = execucao.executar(
                engine_teste, None, configuracao_teste(), "open-meteo-mare", outro, conector=Lento()
            )
            assert r["status"] == "falha" and "Outra coleta" in r["erro"]
        finally:
            liberar.set()
        assert f.result()["status"] == "sucesso"
    r = execucao.executar(engine_teste, None, configuracao_teste(), fonte, eid, conector=Lento())
    assert r["status"] == "sucesso" and chamadas == [eid]
