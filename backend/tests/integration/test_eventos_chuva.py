"""Histórico de eventos de chuva e relatório executivo pela API, com Postgres real (RN-05, RN-01, RN-13, RF-19).

Os dados de chuva, maré e saúde abaixo são dados de teste, semeados dentro da transação desfeita ao fim."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from climasense.servicos import saude_agravos
from climasense.territorio import carga
from tests.conftest import URL_TESTE, _alembic, precisa_postgres, recriar_banco
from tests.integration.apoio import Relogio, cliente, criar_conta, entrar

pytestmark = [precisa_postgres, pytest.mark.integracao]
API = "/api/v1"
INICIO = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)  # 09:00 no Recife

DECLARAR = text(
    "insert into app.estagio_declaracoes (territorio_id, estagio, justificativa, lote_id, autor_id, declarado_em) "
    "values (:t, :e, 'teste', gen_random_uuid(), :a, :d)"
)


@pytest.fixture
def equipe(sessao):
    carga.sincronizar_territorios(sessao, carga.geo_local())
    relogio = Relogio()
    pessoas = {"relogio": relogio}
    for email, papeis in [
        ("ana@recife.pe.gov.br", ["analista"]),
        ("cris@recife.pe.gov.br", ["coordenacao"]),
        ("davi@recife.pe.gov.br", ["analista"]),
    ]:
        nome = email.split("@")[0]
        pessoas[nome + "_u"] = criar_conta(sessao, email, papeis, nome=nome.capitalize())
        c = cliente(sessao, relogio)
        entrar(c, email)
        pessoas[nome] = c
    return pessoas


def _abrir(c, **extra):
    r = c.post(f"{API}/eventos", json={"inicio_em": INICIO.isoformat(), **extra})
    assert r.status_code == 201, r.text
    return r.json()


def _item(c, eid, **corpo):
    return c.post(f"{API}/eventos/{eid}/itens", json=corpo)


def _execucao(sessao, fonte: str) -> str:
    return str(
        sessao.execute(
            text(
                "insert into app.etl_execucoes (fonte_id, status, fim) values (:f, 'sucesso', now()) returning id"
            ),
            {"f": fonte},
        ).scalar_one()
    )


def test_fluxo_completo_e_ninguem_aprova_o_proprio(equipe, sessao):
    ana, cris, davi = equipe["ana"], equipe["cris"], equipe["davi"]
    ev = _abrir(ana, distritos_afetados=["ds-4", "ds-4", "ds-1"])
    assert ev["situacao"] == "aberto" and ev["nome"] == "Evento de 13/10/2026"
    assert ev["distritos_afetados"] == ["ds-4", "ds-1"]
    assert [d["nome"] for d in ev["distritos"]] == ["Distrito 4", "Distrito 1"]
    eid = ev["id"]

    r = _item(
        cris, eid, tipo="comunicado", texto="APAC emite aviso laranja", fonte="APAC", equipes_mobilizadas=4
    )
    assert r.status_code == 201, r.text
    r = _item(cris, eid, tipo="observacao", texto="Dois alagamentos.")
    assert r.json()["linha_do_tempo"][-1]["fonte"] == "Registro da equipe"
    assert len(r.json()["linha_do_tempo"]) == 2
    # comunicado sem fonte, tipo estágio sem estágio, hora anterior ao início e hora futura
    assert _item(ana, eid, tipo="comunicado", texto="x").status_code == 422
    assert _item(ana, eid, tipo="estagio", texto="x").status_code == 422
    antes = (INICIO - timedelta(hours=1)).isoformat()
    assert _item(ana, eid, tipo="observacao", texto="x", ocorrido_em=antes).status_code == 422
    futuro = (equipe["relogio"].agora + timedelta(hours=2)).isoformat()
    assert _item(ana, eid, tipo="observacao", texto="x", ocorrido_em=futuro).status_code == 422

    # aprovar antes de encerrar não pode
    assert davi.post(f"{API}/eventos/{eid}/aprovar").status_code == 409
    assert ana.post(f"{API}/eventos/{eid}/encerrar", json={"situacao_final": "  "}).status_code == 422
    r = cris.post(
        f"{API}/eventos/{eid}/encerrar",
        json={"situacao_final": "Chuva cessou; vias liberadas.", "pendencias": "Limpar canal X"},
    )
    assert r.status_code == 200 and r.json()["situacao"] == "encerrado" and r.json()["aguarda_aprovacao"]
    assert r.json()["encerrado_por_nome"] == "Cris"
    assert ana.post(f"{API}/eventos/{eid}/encerrar", json={"situacao_final": "outra"}).status_code == 409
    assert _item(ana, eid, tipo="observacao", texto="tarde").status_code == 409

    # ninguém aprova o próprio: nem quem abriu nem quem encerrou
    for quem in (ana, cris):
        r = quem.post(f"{API}/eventos/{eid}/aprovar")
        assert r.status_code == 403, r.text
        assert "não pode aprová-lo" in r.json()["detail"]
    assert ana.get(f"{API}/eventos/{eid}").json()["situacao"] == "encerrado"

    r = davi.post(f"{API}/eventos/{eid}/aprovar")
    assert r.status_code == 200 and r.json()["situacao"] == "aprovado"
    assert r.json()["aprovado_por_nome"] == "Davi" and r.json()["duracao_horas"] is not None
    assert davi.post(f"{API}/eventos/{eid}/aprovar").status_code == 409

    acoes = [
        a
        for (a,) in sessao.execute(
            text("select acao from app.auditoria where alvo_tipo = 'evento_chuva' order by id")
        )
    ]
    assert acoes == [
        "evento_chuva_aberto",
        "evento_chuva_item_registrado",
        "evento_chuva_item_registrado",
        "evento_chuva_encerrado",
        "evento_chuva_aprovado",
    ]


def test_listar_e_abrir_um_evento(equipe):
    ana = equipe["ana"]
    a = _abrir(ana, nome="Chuva de outubro")
    b = ana.post(f"{API}/eventos", json={"inicio_em": (INICIO - timedelta(days=3)).isoformat()}).json()
    lista = ana.get(f"{API}/eventos").json()
    assert [e["id"] for e in lista["itens"]] == [a["id"], b["id"]]  # mais recente primeiro
    assert lista["total"] == 2 and lista["contagens"] == {"aberto": 2}
    assert ana.get(f"{API}/eventos", params={"situacao": "aprovado"}).json()["itens"] == []
    assert ana.get(f"{API}/eventos", params={"situacao": "x"}).status_code == 422
    assert ana.get(f"{API}/eventos/{a['id']}").json()["nome"] == "Chuva de outubro"
    assert ana.get(f"{API}/eventos/00000000-0000-0000-0000-000000000000").status_code == 404


def test_validacoes_da_abertura(equipe):
    ana = equipe["ana"]
    assert ana.post(f"{API}/eventos", json={"distritos_afetados": ["ds-9"]}).status_code == 422
    assert ana.post(f"{API}/eventos", json={"distritos_afetados": ["recife"]}).status_code == 422
    assert ana.post(f"{API}/eventos", json={"fim_em": INICIO.isoformat()}).status_code == 422  # em andamento
    futuro = (equipe["relogio"].agora + timedelta(days=1)).isoformat()
    assert ana.post(f"{API}/eventos", json={"inicio_em": futuro}).status_code == 422


def test_retrospectivo_nasce_encerrado_sem_linha_do_tempo_e_precisa_de_outra_pessoa(equipe):
    ana, cris = equipe["ana"], equipe["cris"]
    corpo = {
        "retrospectivo": True,
        "inicio_em": "2022-06-01T00:00:00Z",
        "fim_em": "2022-06-03T00:00:00Z",
        "situacao_final": "Registro da Defesa Civil",
        "distritos_afetados": ["ds-5"],
    }
    assert ana.post(f"{API}/eventos", json={**corpo, "situacao_final": None}).status_code == 422
    assert ana.post(f"{API}/eventos", json={**corpo, "fim_em": None}).status_code == 422
    ev = ana.post(f"{API}/eventos", json=corpo).json()
    assert ev["situacao"] == "encerrado" and ev["retrospectivo"] and ev["duracao_horas"] == 48.0
    assert _item(ana, ev["id"], tipo="observacao", texto="x").status_code == 409
    assert ana.post(f"{API}/eventos/{ev['id']}/aprovar").status_code == 403
    assert cris.post(f"{API}/eventos/{ev['id']}/aprovar").status_code == 200
    rel = cris.get(f"{API}/eventos/{ev['id']}/relatorio").json()
    assert "retrospectivo" in rel["linha_do_tempo"]["motivo"] and rel["aviso"] is None


def test_relatorio_sem_dados_diz_dados_insuficientes_com_a_fonte(equipe):
    ana = equipe["ana"]
    eid = _abrir(ana)["id"]
    r = ana.get(f"{API}/eventos/{eid}/relatorio")
    assert r.status_code == 200, r.text
    rel = r.json()
    assert rel["aviso"].startswith("Rascunho") and rel["periodo"]["em_andamento"]
    assert rel["evento"]["suficiente"] and rel["evento"]["fonte"]
    blocos = (
        "comunicados",
        "equipes_mobilizadas",
        "distritos_afetados",
        "chuva",
        "mare",
        "acoes",
        "situacao_final",
        "linha_do_tempo",
    )
    for bloco in blocos:
        b = rel[bloco]
        assert not b["suficiente"], bloco
        assert b["motivo"].startswith(("Dados insuficientes", "Não disponível")), (bloco, b["motivo"])
    assert "apac-chuva" in rel["chuva"]["motivo"] and rel["chuva"]["pico_diario_mm"] is None
    assert "open-meteo-mare" in rel["mare"]["motivo"]
    assert not rel["saude"]["suficiente"]
    assert all("infodengue" in i["motivo"] or "sinan" in i["motivo"] for i in rel["saude"]["itens"])
    assert "abrigos" not in rel


def _semear_dados_reais_de_teste(sessao, equipe, bairro):
    for terr, est, quando in [
        (bairro, "alerta", INICIO + timedelta(hours=2)),
        ("ds-1", "atencao", INICIO + timedelta(hours=3)),
        ("ds-2", "critico", INICIO - timedelta(days=30)),  # antes do evento: fica de fora
    ]:
        sessao.execute(DECLARAR, {"t": terr, "e": est, "a": equipe["ana_u"].id, "d": quando})
    # chuva medida
    ex = _execucao(sessao, "apac-chuva")
    sessao.execute(
        text(
            "insert into silver.estacoes (id, fonte_id, codigo_fonte, nome, lat, lon) values "
            "('est-t', 'apac-chuva', 't', 'Teste', -8.05, -34.9)"
        )
    )
    sessao.execute(
        text(
            "insert into silver.apac_chuva_diaria (estacao_id, dia, valor_mm, coletado_em, execucao_id) "
            "values ('est-t', '2026-10-13', 42.5, '2026-10-14T01:00:00Z', :x)"
        ),
        {"x": ex},
    )
    for ds, dia, mm in [
        ("ds-4", "2026-10-13", 42.5),
        ("ds-1", "2026-10-13", 10.0),
        ("ds-4", "2026-10-14", 0.0),
        ("ds-1", "2026-10-20", 99.0),  # depois do evento
    ]:
        sessao.execute(
            text(
                "insert into gold.chuva_apac_diaria (territorio_id, dia, nivel, max_mm, mediana_mm, n_estacoes) "
                "values (:t, :d, 'distrito', :m, :m, 1)"
            ),
            {"t": ds, "d": dia, "m": mm},
        )
    # nível do mar do modelo
    ex = _execucao(sessao, "open-meteo-mare")
    for h, v in [(0, 0.4), (6, 2.1), (12, 0.3)]:
        quando = datetime(2026, 10, 14, 12, tzinfo=UTC) + timedelta(hours=h)
        sessao.execute(
            text(
                "insert into silver.observacoes (fonte_id, variavel, valor, unidade, tipo, observado_em, emitido_em, "
                "coletado_em, execucao_id) values ('open-meteo-mare', 'mare_m', :v, 'm', 'prevista', :t, :e, :e, :x)"
            ),
            {"v": v, "t": quando, "e": quando - timedelta(hours=2), "x": ex},
        )
    # saúde: dengue com 3 casos (suprimido), leptospirose com 12 (publicável); chikungunya sem semana
    semana = saude_agravos.domingo(date(2026, 10, 13))
    for agravo, fonte, casos in [("dengue", "infodengue", 3), ("leptospirose", "sinan-leptospirose", 12)]:
        sessao.execute(
            text(
                "insert into gold.saude_semanal (agravo, fonte_id, ano, semana, inicio, casos, confirmados, "
                "casos_estimados, incompleta) values (:a, :f, 2026, 41, :i, :c, :c, :c + 0.5, false)"
            ),
            {"a": agravo, "f": fonte, "i": semana, "c": casos},
        )
    ex = _execucao(sessao, "infodengue")
    sessao.execute(
        text(
            "insert into silver.infodengue_semanal (agravo, ano, semana, inicio, casos, incompleta, coletado_em, "
            "execucao_id) values ('dengue', 2026, 41, :i, 3, false, '2026-10-14T05:00:00Z', :x)"
        ),
        {"i": semana, "x": ex},
    )
    sessao.commit()


def test_relatorio_consolidado_so_com_dados_existentes(equipe, sessao):
    ana, cris, davi = equipe["ana"], equipe["cris"], equipe["davi"]
    eid = _abrir(ana, distritos_afetados=["ds-4"])["id"]
    _item(ana, eid, tipo="comunicado", texto="Aviso APAC", fonte="APAC", equipes_mobilizadas=6)
    _item(ana, eid, tipo="observacao", texto="Equipes", equipes_mobilizadas=9)
    bairro = sessao.execute(
        text("select id from app.territorios where pai_id = 'ds-4' order by id limit 1")
    ).scalar_one()
    r = ana.post(
        f"{API}/acoes",
        json={
            "territorio_id": bairro,
            "tipo": "visita",
            "descricao": "Visita ao canal",
            "responsavel": "Fulano de Tal",
            "situacao": "em_andamento",
            "inicio_em": (INICIO + timedelta(hours=4)).isoformat(),
        },
    )
    assert r.status_code == 201, r.text
    antigo = ana.post(
        f"{API}/acoes",
        json={
            "territorio_id": "ds-1",
            "tipo": "orientacao",
            "descricao": "Fora da janela",
            "situacao": "concluida",
            "inicio_em": "2026-01-01T10:00:00Z",
            "fim_em": "2026-01-01T12:00:00Z",
        },
    )
    assert antigo.status_code == 201, antigo.text
    _semear_dados_reais_de_teste(sessao, equipe, bairro)

    r = cris.post(
        f"{API}/eventos/{eid}/encerrar",
        json={"situacao_final": "Normalizado", "pendencias": "Canal X", "fim_em": "2026-10-15T15:00:00Z"},
    )
    assert r.status_code == 200, r.text
    rel = davi.get(f"{API}/eventos/{eid}/relatorio").json()
    assert rel["periodo"]["desde"] == "2026-10-13" and rel["periodo"]["ate"] == "2026-10-15"
    assert rel["aviso"].startswith("Rascunho")

    com = rel["comunicados"]
    assert com["suficiente"] and com["itens"][0]["fonte"] == "APAC" and com["atualizado_em"]
    eq = rel["equipes_mobilizadas"]
    assert eq["suficiente"] and eq["maior_numero"] == 9 and len(eq["registros"]) == 2

    dist = rel["distritos_afetados"]
    por = {d["distrito_id"]: d for d in dist["com_estagio_declarado"]}
    assert set(por) == {
        "ds-4",
        "ds-1",
    }  # o estágio de 30 dias antes fica de fora; o do bairro conta no distrito
    assert por["ds-4"]["maior_estagio"] == "alerta" and por["ds-4"]["distrito_nome"] == "Distrito 4"
    assert [d["distrito_id"] for d in dist["registrados"]] == ["ds-4"]

    chuva = rel["chuva"]
    assert (
        chuva["suficiente"]
        and chuva["pico_diario_mm"] == 42.5
        and chuva["pico_distrito_nome"] == "Distrito 4"
    )
    dias = {d["dia"]: d for d in chuva["dias"]}
    assert set(dias) == {"2026-10-13", "2026-10-14"}  # 20/10 fica fora do evento
    assert dias["2026-10-14"]["maximo_mm"] == 0.0  # zero medido é zero (RN-02)
    assert chuva["atualizado_em"].startswith("2026-10-14T01:00") and "apac-chuva" in chuva["fonte"]

    mare = rel["mare"]
    assert mare["suficiente"] and mare["maximo_m"] == 2.1 and "não é medição" in mare["fonte"]
    assert mare["dias"][0]["dia"] == "2026-10-14" and mare["dias"][0]["minimo_m"] == 0.3

    saude = {i["agravo"]: i for i in rel["saude"]["itens"]}
    assert saude["dengue"]["semanas"][0]["casos"] is None and saude["dengue"]["semanas"][0]["suprimido"]
    assert saude["dengue"]["total_casos"] is None and saude["dengue"]["atualizado_em"]
    assert saude["leptospirose"]["total_casos"] == 12 and saude["leptospirose"]["semanas"][0]["casos"] == 12
    assert not saude["chikungunya"]["suficiente"] and "infodengue" in saude["chikungunya"]["motivo"]

    acoes = rel["acoes"]
    assert acoes["suficiente"] and [a["descricao"] for a in acoes["itens"]] == ["Visita ao canal"]
    assert "responsavel" not in acoes["itens"][0] and "Fulano" not in str(rel)  # RN-13

    tl = rel["linha_do_tempo"]["itens"]
    assert [m["em"] for m in tl] == sorted(m["em"] for m in tl)
    assert {m["tipo"] for m in tl} == {"comunicado", "observacao", "estagio", "acao"}
    assert all(m["fonte"] for m in tl)
    assert not any("Sanitário" in m["texto"] for m in tl)

    sf = rel["situacao_final"]
    assert sf["suficiente"] and sf["situacao_final"] == "Normalizado" and sf["pendencias"] == "Canal X"
    assert not sf["aprovada"]

    assert davi.post(f"{API}/eventos/{eid}/aprovar").status_code == 200
    rel = davi.get(f"{API}/eventos/{eid}/relatorio").json()
    assert rel["aviso"] is None and rel["situacao_final"]["aprovada"]
    assert rel["evento"]["aprovado_por_nome"] == "Davi"
    for nome, b in rel.items():
        if isinstance(b, dict) and "fonte" in b:
            assert b["fonte"], nome  # RF-19


def test_banco_barra_aprovar_o_proprio_e_alterar_o_aprovado(equipe, sessao):
    ana, davi = equipe["ana"], equipe["davi"]
    eid = _abrir(ana)["id"]
    ana.post(f"{API}/eventos/{eid}/encerrar", json={"situacao_final": "ok"})
    with pytest.raises(IntegrityError), sessao.begin_nested():
        sessao.execute(
            text(
                "update app.eventos_chuva set situacao = 'aprovado', aprovado_por = :u, aprovado_em = now() "
                "where id = :i"
            ),
            {"u": equipe["ana_u"].id, "i": eid},
        )
    assert davi.post(f"{API}/eventos/{eid}/aprovar").status_code == 200
    for sql in (
        "update app.eventos_chuva set situacao_final = 'adulterado' where id = :i",
        "delete from app.eventos_chuva where id = :i",
    ):
        with pytest.raises(DBAPIError), sessao.begin_nested():
            sessao.execute(text(sql), {"i": eid})


def test_itens_sao_somente_inclusao(equipe, sessao):
    ana = equipe["ana"]
    eid = _abrir(ana)["id"]
    _item(ana, eid, tipo="observacao", texto="a")
    for sql in ("update app.evento_chuva_itens set texto = 'b'", "delete from app.evento_chuva_itens"):
        with pytest.raises(DBAPIError), sessao.begin_nested():
            sessao.execute(text(sql))


def test_privilegios_do_papel_da_aplicacao(engine_teste):
    with engine_teste.connect() as c:

        def tem(t, p):
            return c.execute(
                text("select has_table_privilege('climasense_app', :t, :p)"), {"t": f"app.{t}", "p": p}
            ).scalar()

        assert tem("eventos_chuva", "SELECT") and tem("eventos_chuva", "INSERT")
        assert tem("eventos_chuva", "UPDATE")
        assert not tem("eventos_chuva", "DELETE") and not tem("eventos_chuva", "TRUNCATE")
        assert tem("evento_chuva_itens", "SELECT") and tem("evento_chuva_itens", "INSERT")
        for p in ("UPDATE", "DELETE", "TRUNCATE"):
            assert not tem("evento_chuva_itens", p)


def test_migracao_0024_sobe_e_desce():
    engine = recriar_banco(URL_TESTE)
    try:

        def existe(t):
            with engine.connect() as c:
                return c.execute(text("select to_regclass(:t)"), {"t": t}).scalar() is not None

        assert existe("app.eventos_chuva") and existe("app.evento_chuva_itens")
        command.downgrade(_alembic(URL_TESTE), "0024-1")
        assert not existe("app.eventos_chuva") and not existe("app.evento_chuva_itens")
        command.upgrade(_alembic(URL_TESTE), "head")
        assert existe("app.eventos_chuva")
    finally:
        engine.dispose()
        recriar_banco(URL_TESTE).dispose()
