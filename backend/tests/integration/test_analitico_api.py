"""T6.2–T6.5: séries com lacunas, referência, sazonalidade, estatística, cenários e vacinação agregada."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import text

from climasense.territorio import carga
from tests.conftest import precisa_postgres
from tests.integration.apoio import Relogio, cliente, criar_conta, entrar

pytestmark = [precisa_postgres, pytest.mark.integracao]
API = "/api/v1"


@pytest.fixture
def c(sessao):
    carga.sincronizar_territorios(sessao, carga.geo_local())
    http = cliente(sessao, Relogio())
    criar_conta(sessao, "ana@recife.pe.gov.br", ["analista"])
    entrar(http, "ana@recife.pe.gov.br")
    return http


def _execucao(sessao, fonte: str) -> str:
    return str(
        sessao.execute(
            text(
                "insert into app.etl_execucoes (fonte_id, status, fim) values (:f, 'sucesso', now()) returning id"
            ),
            {"f": fonte},
        ).scalar_one()
    )


def _chuva(sessao, territorio: str, inicio: date, dias: int, valor=2.0, faltando=()):
    for i in range(dias):
        d = inicio + timedelta(days=i)
        if d in faltando:
            continue
        sessao.execute(
            text("insert into gold.chuva_diaria values (:t, :d, :v, 24, 100, 'derivada')"),
            {"t": territorio, "d": d, "v": valor},
        )


def test_serie_com_lacunas_null_e_resumo_que_as_cita(c, sessao):
    _execucao(sessao, "open-meteo-historico")
    _chuva(sessao, "ds-4", date(2026, 9, 1), 30, faltando={date(2026, 9, 10), date(2026, 9, 11)})
    sessao.execute(
        text(
            "insert into gold.referencia_mensal values ('ds-4', 9, 100, 95, '{2021,2022,2023,2024,2025}', 98)"
        )
    )
    r = c.get(
        f"{API}/series", params={"territorio_id": "ds-4", "inicio": "2026-09-01", "fim": "2026-09-30"}
    ).json()
    pontos = {p["t"]: p["valor"] for p in r["dados"]["pontos"]}
    assert pontos["2026-09-10"] is None and pontos["2026-09-09"] == 2.0
    assert r["dados"]["lacunas_dias"] == 2 and "Faltam dados em 2 dias." in r["dados"]["resumo"]
    assert r["meta"]["fontes"][0]["id"] == "open-meteo-historico" and r["meta"]["cobertura_pct"] == 93.3
    mensal = c.get(
        f"{API}/series",
        params={"territorio_id": "ds-4", "inicio": "2026-09-01", "fim": "2026-09-30", "frequencia": "mensal"},
    ).json()
    assert mensal["dados"]["pontos"][0]["valor"] is None  # mês com lacuna não vira soma parcial
    # bairro → distrito, com aviso (RN-07)
    b = c.get(
        f"{API}/series",
        params={"territorio_id": "bairro-afogados", "inicio": "2026-09-01", "fim": "2026-09-05"},
    ).json()
    assert b["dados"]["territorio_id"] == "ds-5" and "só por distrito" in b["meta"]["avisos"][0]


def test_serie_sem_dado_e_variavel_sem_fonte(c):
    r = c.get(
        f"{API}/series", params={"territorio_id": "ds-1", "inicio": "2026-01-01", "fim": "2026-01-31"}
    ).json()
    assert r["meta"]["dados_insuficientes"] is True and all(p["valor"] is None for p in r["dados"]["pontos"])
    m = c.get(f"{API}/series", params={"variavel": "mare_m"}).json()
    assert m["meta"]["dados_insuficientes"] and "Marinha" in m["meta"]["avisos"][0]


def test_estatisticas_com_aviso_de_serie_curta(c, sessao):
    _chuva(sessao, "ds-2", date(2026, 9, 1), 10, valor=3.0)
    r = c.get(
        f"{API}/series/estatisticas",
        params={"territorio_id": "ds-2", "inicio": "2026-09-01", "fim": "2026-09-10"},
    ).json()
    assert r["dados"]["n"] == 10 and r["dados"]["serie_curta"] is True
    assert "Série curta: não use para caracterizar o clima." in r["meta"]["avisos"]
    media = next(m for m in r["dados"]["medidas"] if m["chave"] == "media")
    assert media["valor"] == 3.0 and media["texto"] == "3,0 mm"


def test_referencia_e_sazonalidade(c, sessao):
    sessao.execute(
        text("insert into gold.referencia_mensal values ('recife', 6, 300.5, 280, '{2021,2022}', 99)")
    )
    sessao.execute(
        text(
            "insert into gold.chuva_mensal values ('recife', '2025-06-01', 310, 30, 100, 'derivada'), ('recife', '2025-07-01', 50, 20, 64.5, 'derivada')"
        )
    )
    ref = c.get(f"{API}/series/referencia").json()
    assert ref["dados"]["meses"][0]["anos_usados"] == [2021, 2022] and "80%" in ref["dados"]["metodo"]
    saz = c.get(f"{API}/series/sazonalidade").json()["dados"]
    assert saz["anos"] == [2025]
    assert [(x["mes"], x["valor"]) for x in saz["celulas"]] == [(6, 310.0), (7, None)]


def test_cenario_sem_mare_e_insuficiente_e_fica_registrado(c, sessao):
    r = c.get(f"{API}/cenarios", params={"territorio_id": "ds-3", "horizonte_h": 24}).json()
    e = r["dados"]["estimativa"]
    assert e["experimental"] is True and e["prioridade"] == "dados_insuficientes"
    assert r["meta"]["dados_insuficientes"] and r["meta"]["avisos"][0].startswith("Experimental")
    n = sessao.execute(
        text("select count(*) from silver.previsoes_emitidas where territorio_id = 'ds-3'")
    ).scalar()
    assert n == 1  # cada chamada fica registrada (RF-09.8)


def test_vacinacao_agregada_com_amostra_e_supressao(c, sessao):
    ex = _execucao(sessao, "vacinacao")
    sessao.execute(
        text(
            "insert into gold.vacinacao_distrito_mes values (4, '2021-03-01', 120, 120, 1400000, false, :e), "
            "(4, '2021-04-01', null, 3, 1400000, true, :e)"
        ),
        {"e": ex},
    )
    r = c.get(f"{API}/saude/vacinacao", params={"territorio_id": "ds-4"}).json()
    assert r["meta"]["amostra"] == {"n": 123, "total_fonte": 1400000}
    assert [x["doses"] for x in r["dados"]] == [120, None] and r["dados"][1]["suprimido"] is True
    assert any("Amostra de 123 registros" in a for a in r["meta"]["avisos"])
