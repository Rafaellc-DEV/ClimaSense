from datetime import UTC, datetime, timedelta

import mongomock
import pytest
from sqlalchemy import text

from climasense.etl import execucao, gold
from climasense.etl.conectores.open_meteo import (
    ConectorOpenMeteoHistorico,
    ConectorOpenMeteoMare,
    ConectorOpenMeteoPrevisao,
)
from climasense.etl.conectores.vacinacao import ConectorVacinacao
from climasense.etl.extract import Extract
from climasense.territorio import carga
from tests.conftest import configuracao_teste, precisa_postgres
from tests.unit.etl.registros_ckan import REGISTROS, HttpCkan

pytestmark = [precisa_postgres, pytest.mark.integracao]


class HttpOpenMeteo:
    """Responde no formato da API Open-Meteo (hourly.time + hourly.<variável>). Dublê de rede."""

    def __init__(self, variavel, valores, inicio="2026-09-01T00:00"):
        t0 = datetime.fromisoformat(inicio)
        self.corpo = {
            "hourly": {
                "time": [(t0 + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M") for h in range(len(valores))],
                variavel: valores,
            }
        }

    def get(self, url, params, timeout):
        return type("R", (), {"json": lambda s: self.corpo, "raise_for_status": lambda s: None})()


@pytest.fixture
def base(engine_teste):
    with engine_teste.begin() as c:
        c.execute(
            text(
                "truncate silver.observacoes, silver.vacinados, gold.vacinacao_distrito_mes, gold.chuva_diaria, "
                "gold.chuva_mensal, gold.referencia_mensal, app.etl_execucoes cascade"
            )
        )
    from sqlalchemy.orm import Session

    with Session(engine_teste) as s:
        carga.sincronizar_territorios(s, carga.geo_local())
    return engine_teste, mongomock.MongoClient(), configuracao_teste(supressao_minima=2)


def test_vacinacao_de_ponta_a_ponta_com_registro_da_execucao(base):
    engine, mongo, config = base
    ex = execucao.iniciar(engine, "vacinacao")
    conector = ConectorVacinacao(
        extract=Extract("u", "r", 100, http=HttpCkan(REGISTROS * 3, total=1_400_000))
    )
    r = execucao.executar(engine, mongo, config, "vacinacao", ex, conector=conector)
    assert r["status"] == "sucesso" and r["lidos"] == 12 and r["gravados"] == 1
    with engine.connect() as c:
        assert c.execute(text("select count(*) from public.silver_vacinados")).scalar() == 1
        linha = c.execute(text("select * from gold.vacinacao_distrito_mes")).mappings().one()
        assert (linha["distrito_codigo"], linha["amostra_n"], linha["total_fonte"]) == (4, 1, 1_400_000)
        assert linha["suprimido"] is True and linha["doses"] is None  # 1 < supressão 2 (RN-13)
        ex_db = c.execute(
            text("select status, lidos, gravados, descartados, motivos_descarte from app.etl_execucoes")
        ).one()
        assert ex_db[:4] == ("sucesso", 12, 1, 11)


def test_falha_registra_mensagem_sem_segredo_e_nao_apaga_nada(base):
    engine, mongo, config = base

    class HttpQuebrado:
        def get(self, *a, **k):
            import requests

            raise requests.ConnectionError("mongodb+srv://u:senha-real@x.invalid recusou")

    ex = execucao.iniciar(engine, "vacinacao")
    r = execucao.executar(
        engine,
        mongo,
        config,
        "vacinacao",
        ex,
        conector=ConectorVacinacao(extract=Extract("u", "r", 10, http=HttpQuebrado())),
    )
    assert r["status"] == "falha" and "senha-real" not in r["erro"] and "não respondeu" in r["erro"]
    assert (
        execucao.executar(
            engine, mongo, config, "ana-telemetria", execucao.iniciar(engine, "ana-telemetria")
        )["status"]
        == "falha"
    )


def test_open_meteo_historico_nulo_nao_vira_zero_e_gold_e_reproduzivel(base):
    engine, mongo, config = base
    valores = [0.0] * 24 + [1.5] * 12 + [None] * 12  # dia 1: 0 mm medido; dia 2: metade sem dado
    conector = ConectorOpenMeteoHistorico(
        http=HttpOpenMeteo("precipitation", valores, "2026-09-01T03:00")
    )  # 00:00 no Recife
    r = execucao.executar(
        engine, mongo, config, conector.id, execucao.iniciar(engine, conector.id), conector=conector
    )
    assert r["status"] == "sucesso" and r["gravados"] == 8 * 48
    with engine.connect() as c:
        nulos, zeros = c.execute(
            text(
                "select count(*) filter (where valor is null), count(*) filter (where valor = 0) "
                "from silver.observacoes"
            )
        ).one()
        assert (nulos, zeros) == (8 * 12, 8 * 24)
        dia = c.execute(
            text(
                "select acumulado_mm, cobertura_pct from gold.chuva_diaria where territorio_id='ds-4' order by dia"
            )
        ).all()
        assert dia == [
            (0.0, 100.0),
            (18.0, 50.0),
        ]  # 0 mm medido ≠ sem dado; dia incompleto mostra a cobertura
        assert gold.verificar(c) == {
            "gold.chuva_diaria": 0,
            "gold.chuva_mensal": 0,
            "gold.referencia_mensal": 0,
        }


def test_previsao_e_mare_guardam_emissao_e_horizonte(base):
    engine, mongo, config = base
    agora = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    inicio = agora.strftime("%Y-%m-%dT%H:%M")
    for conector in (
        ConectorOpenMeteoPrevisao(http=HttpOpenMeteo("precipitation", [0.2] * 72, inicio)),
        ConectorOpenMeteoMare(http=HttpOpenMeteo("sea_level_height_msl", [1.1] * 72, inicio)),
    ):
        r = execucao.executar(
            engine, mongo, config, conector.id, execucao.iniciar(engine, conector.id), conector=conector
        )
        assert r["status"] == "sucesso"
    with engine.connect() as c:
        assert (
            c.execute(
                text(
                    "select count(*) from silver.observacoes where variavel='mare_m' and territorio_id='recife'"
                )
            ).scalar()
            == 72
        )
        assert (
            c.execute(text("select max(horizonte_h) from silver.observacoes where tipo='prevista'")).scalar()
            >= 70
        )
        assert (
            c.execute(
                text("select count(*) from silver.observacoes where tipo='prevista' and emitido_em is null")
            ).scalar()
            == 0
        )
