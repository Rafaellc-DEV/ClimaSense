"""Saúde depois da chuva de ponta a ponta no Postgres de teste: conectores (com as amostras reais de
tests/unit/etl/fixtures) → silver → gold reproduzível → rotas /saude/* e /ocorrencias/historico.

Tudo dentro de uma transação desfeita no fim."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import text

from climasense.etl import gold
from climasense.etl.conectores.alagamento import ConectorRecifeAlagamento
from climasense.etl.conectores.arboviroses import ConectorRecifeArboviroses
from climasense.etl.conectores.infodengue import ConectorInfoDengue
from climasense.etl.conectores.leptospirose import ConectorSinanLeptospirose
from tests.conftest import precisa_postgres
from tests.integration.apoio import Relogio, cliente, criar_conta, entrar
from tests.integration.test_etl_chuva import ambiente, rodar  # noqa: F401 — fixture compartilhada
from tests.unit.etl.test_conectores_chuva import FIX, Http, Resposta
from tests.unit.etl.test_conectores_saude import (
    CAMPOS_LEPTO,
    LINHAS_LEPTO,
    FtpFalso,
    _http_arbo,
    _infodengue,
    montar_dbc,
)

pytestmark = [precisa_postgres, pytest.mark.integracao]
AGORA = datetime(2026, 11, 5, 15, 0, tzinfo=UTC)
NOVAS = ("gold.saude_semanal", "gold.arboviroses_bairro_ano", "gold.ocorrencias_bairro")


def _carregar(engine, mongo, config):
    http, _ = _infodengue()
    rodar(engine, mongo, config, ConectorInfoDengue(http=http), agora=AGORA)
    ftp = FtpFalso(
        {("PRELIM", "LEPTBR26.dbc"): ("2026-11-03T14:16:00Z", montar_dbc(CAMPOS_LEPTO, LINHAS_LEPTO))}
    )
    rodar(engine, mongo, config, ConectorSinanLeptospirose(ftp=ftp), agora=AGORA)
    rodar(engine, mongo, config, ConectorRecifeArboviroses(http=_http_arbo()), agora=AGORA)
    dc = (FIX / "defesa_civil_2024_deslizamento_amostra.csv").read_bytes()
    rodar(
        engine,
        mongo,
        config,
        ConectorRecifeAlagamento(
            http=Http({"/2024.csv": Resposta(conteudo=dc)}), recursos={2024: "https://d/2024.csv"}
        ),
        agora=AGORA,
    )


def _equipe(db):
    relogio = Relogio()
    relogio.agora = AGORA
    c = cliente(db, relogio)
    criar_conta(db, "vigidesastres@recife.pe.gov.br", ["analista"])
    assert entrar(c, "vigidesastres@recife.pe.gov.br").status_code == 200
    return c


def test_saude_semanal_bairros_e_onde_ja_aconteceu(ambiente):  # noqa: F811
    engine, mongo, config, db = ambiente
    _carregar(engine, mongo, config)
    dif = gold.verificar(engine.c)
    assert {t: dif[t] for t in NOVAS} == dict.fromkeys(NOVAS, 0)
    # nada pessoal na bronze: só contagens e resumos de arquivo
    assert mongo["bronze"]["sinan_leptospirose"].count_documents({"tipo": "agregado"}) > 0
    assert mongo["bronze"]["recife_arboviroses"].count_documents({"nm_logrado": {"$exists": True}}) == 0
    # chuva semanal (ERA5) para o gráfico: 3 dias de uma semana e 1 de outra
    for dia, mm in ((date(2026, 10, 25), 10.0), (date(2026, 10, 26), 5.5), (date(2026, 10, 27), None),
                    (date(2026, 11, 1), 2.0)):  # fmt: skip
        engine.c.execute(
            text("insert into gold.chuva_diaria values ('recife', :d, :mm, 24, 100, 'derivada')"),
            {"d": dia, "mm": mm},
        )
    c = _equipe(db)

    r = c.get("/api/v1/saude/resumo")
    assert r.status_code == 200, r.text
    corpo = r.json()
    agravos = {a["agravo"]: a for a in corpo["dados"]["agravos"]}
    assert set(agravos) == {"dengue", "chikungunya", "leptospirose"}
    dengue = agravos["dengue"]
    assert dengue["ultima_semana"] == {"ano": 2026, "semana": 43, "inicio": "2026-10-25"}
    assert (dengue["casos"], dengue["casos_estimados"], dengue["nivel_alerta"], dengue["incompleta"]) == (
        36,
        221.0,
        2,
        True,
    )
    # nowcast das 4 últimas (221+232+209+212) contra as 4 anteriores (217+264+268+265)
    assert dengue["variacao_4s_pct"] == round((874 - 1014) / 1014 * 100, 1)
    assert agravos["chikungunya"]["ultima_semana"] is None  # sem série: ausente, não zero
    lepto = agravos["leptospirose"]
    assert lepto["ultima_semana"]["inicio"] == "2026-10-04" and lepto["nivel_alerta"] is None
    assert corpo["dados"]["janela_leptospirose"] is None  # nenhum gatilho registrado
    assert {f["id"] for f in corpo["meta"]["fontes"]} >= {"infodengue", "sinan-leptospirose"}

    r = c.get("/api/v1/saude/semanal", params={"agravo": "dengue", "desde": "2026-10-01"})
    assert r.status_code == 200, r.text
    serie = r.json()["dados"]
    assert [i["semana"] for i in serie["itens"]] == [39, 40, 41, 42, 43]  # desde o domingo 27/09
    assert serie["itens"][-1]["ic_inf"] == 123 and serie["itens"][-1]["ic_sup"] == 414
    assert serie["chuva"] == [
        {"inicio": "2026-10-25", "chuva_mm": 15.5, "dias_com_dado": 2},
        {"inicio": "2026-11-01", "chuva_mm": 2.0, "dias_com_dado": 1},
    ]
    r = c.get("/api/v1/saude/semanal", params={"agravo": "leptospirose", "desde": "2026-05-01"})
    lep = {i["inicio"]: i for i in r.json()["dados"]["itens"]}
    assert (lep["2026-05-10"]["casos"], lep["2026-05-10"]["confirmados"]) == (3, 2)
    assert lep["2026-10-04"]["incompleta"] is True
    assert c.get("/api/v1/saude/semanal", params={"agravo": "zika"}).status_code == 422

    r = c.get("/api/v1/saude/bairros", params={"agravo": "dengue"})
    assert r.status_code == 200, r.text
    b = r.json()["dados"]
    assert b["ano"] == 2025 and b["anos_disponiveis"] == [2025, 2015]
    por_bairro = {i["bairro_id"]: i for i in b["itens"]}
    assert len(por_bairro) == 94
    # RNF-03/RN-13: 1 a 4 casos saem nulos e marcados; zero medido continua zero
    assert por_bairro["bairro-pina"]["casos"] is None and por_bairro["bairro-pina"]["suprimido"] is True
    assert por_bairro["bairro-pina"]["distrito_id"] == "ds-6"
    assert por_bairro["bairro-torre"]["casos"] == 0 and por_bairro["bairro-torre"]["notificados"] is None
    assert b["total_confirmados"] is None  # 3 casos no total: pequeno demais
    assert b["total_notificados"] == 10
    assert b["confirmados_sem_bairro"] is None and b["sem_bairro_suprimido"] is True
    assert r.json()["meta"]["supressao_minima"] == 5
    assert r.json()["meta"]["recorte"]["granularidade"] == "bairro"
    vazio = c.get("/api/v1/saude/bairros", params={"agravo": "chikungunya"}).json()
    assert vazio["dados"]["itens"] == [] and vazio["meta"]["dados_insuficientes"] is True

    r = c.get("/api/v1/ocorrencias/historico", params={"tipo": "deslizamento"})
    assert r.status_code == 200, r.text
    h = r.json()["dados"]
    assert h["total_registros"] == 4 and h["bairros_com_registro"] == 4
    assert {i["bairro_id"] for i in h["itens"]} >= {"bairro-dois-unidos", "bairro-agua-fria"}
    assert h["periodo_inicio"] == "2024-04-10" and h["periodo_fim"] == "2024-06-15"
    alag = c.get("/api/v1/ocorrencias/historico", params={"tipo": "alagamento"}).json()["dados"]
    assert alag["total_registros"] == 2
    # o estágio continua contando só alagamento como "ocorrências históricas"
    assert engine.c.execute(text("select count(*) from gold.alagamento_bairro_dia")).scalar() == 2


def test_janela_de_leptospirose_abre_com_estagio_e_com_chuva_medida(ambiente):  # noqa: F811
    engine, mongo, config, db = ambiente
    c = _equipe(db)
    autor = db.execute(text("select id from app.usuarios limit 1")).scalar_one()
    db.execute(
        text(
            "insert into app.estagio_declaracoes (territorio_id, estagio, justificativa, lote_id, autor_id, "
            "declarado_em) values ('recife', 'critico', 'chuva forte', :l, :a, :em)"
        ),
        {"l": uuid.uuid4(), "a": autor, "em": AGORA - timedelta(days=8)},
    )
    db.execute(
        text(
            "insert into gold.chuva_apac_diaria values ('ds-4', :d, 'distrito', 72.4, 40.0, 3, null), "
            "('ds-5', :d, 'distrito', 80.0, 50.0, 3, 'recife'), ('ds-6', :d, 'distrito', 30.0, 20.0, 2, null)"
        ),
        {"d": date(2026, 11, 1)},
    )  # ds-5 herdou do Recife (não mediu) e ds-6 ficou abaixo do limiar de Alerta (50 mm): não contam
    jan = c.get("/api/v1/saude/resumo").json()["dados"]["janela_leptospirose"]
    assert jan["ativa"] is True
    assert (jan["inicio"], jan["fim"]) == ("2026-10-28", "2026-12-01")
    assert jan["dia_da_janela"] == 9 and jan["origens"] == ["chuva", "estagio"]
    assert [t["id"] for t in jan["territorios"]] == ["recife", "ds-4"]
    assert "Crítico" in jan["motivo"] and "72 mm" in jan["motivo"]


def test_rotas_de_saude_exigem_login(ambiente):  # noqa: F811
    _, _, _, db = ambiente
    c = cliente(db, Relogio())
    for rota in ("/api/v1/saude/resumo", "/api/v1/saude/semanal", "/api/v1/saude/bairros",
                 "/api/v1/ocorrencias/historico"):  # fmt: skip
        assert c.get(rota).status_code == 401
