"""Onda 1, Etapa 3: simulador de cenário (RF-23 a RF-25, RF-28) e cenários salvos (RF-27)."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from climasense.territorio import carga
from tests.conftest import precisa_postgres
from tests.integration.apoio import Relogio, cliente, criar_conta, entrar

pytestmark = [precisa_postgres, pytest.mark.integracao]
API = "/api/v1/cenarios"
PREMISSAS = {
    "chuva_prevista_mm": 72,
    "duracao_h": 24,
    "chuva_acumulada_mm": 40,
    "mare_m": 2.3,
    "horizonte_h": 24,
}


@pytest.fixture
def equipe(sessao):
    carga.sincronizar_territorios(sessao, carga.geo_local())
    relogio = Relogio()
    contas = {"relogio": relogio}
    for nome, papeis in (("analista", ["analista"]), ("outra", ["analista"]), ("leitor", ["revisor"])):
        criar_conta(sessao, f"{nome}@recife.pe.gov.br", papeis, nome=nome.capitalize())
        c = cliente(sessao, relogio)
        assert entrar(c, f"{nome}@recife.pe.gov.br").status_code == 200
        contas[nome] = c
    return contas


def _bairros(sessao, n=3) -> list[str]:
    return [
        b
        for (b,) in sessao.execute(
            text("select id from app.territorios where tipo = 'bairro' order by id limit :n"), {"n": n}
        )
    ]


def _carga(sessao, linhas: list[tuple[str, str, int]]) -> None:
    ex = sessao.execute(
        text(
            "insert into app.etl_execucoes (fonte_id, status, fim) "
            "values ('recife-alagamento', 'sucesso', now()) returning id"
        )
    ).scalar_one()
    for territorio, tipo, quantas in linhas:
        for _ in range(quantas):
            sessao.execute(
                text(
                    "insert into silver.ocorrencias (fonte_id, territorio_id, registrado_em, tipo, execucao_id) "
                    "values ('recife-alagamento', :t, '2020-05-01T10:00:00Z', :tipo, :e)"
                ),
                {"t": territorio, "tipo": tipo, "e": ex},
            )


def _item(corpo, tid):
    return next(i for i in corpo["dados"]["itens"] if i["territorio_id"] == tid)


# ------------------------------------------------------------------ simular
def test_sem_carga_tudo_e_sem_dados_nunca_classe_baixa(equipe):
    r = equipe["leitor"].post(f"{API}/simular", json=PREMISSAS)
    assert r.status_code == 200, r.text
    d = r.json()["dados"]
    assert len(d["itens"]) == 102  # 94 bairros + 8 distritos
    assert {i["classe_alagamento"] for i in d["itens"]} == {"sem_dados"}
    assert {i["confianca"] for i in d["itens"]} == {"insuficiente"}
    assert d["experimental"] is True and d["tempo_calculo_ms"] >= 0
    assert d["resumo"]["impacto_pessoas_aviso"].startswith("Dados insuficientes")
    assert all(i["impacto_pessoas"] is None for i in d["itens"])
    assert r.json()["meta"]["fontes"][0]["id"] == "recife-alagamento"


def test_simulacao_com_historico_classifica_por_bairro(equipe, sessao):
    b1, b2, b3 = _bairros(sessao)
    _carga(sessao, [(b1, "alagamento", 14), (b1, "deslizamento", 2), (b2, "alagamento", 0)])
    corpo = equipe["leitor"].post(f"{API}/simular", json=PREMISSAS).json()
    i1, i3 = _item(corpo, b1), _item(corpo, b3)
    # 72 mm em 24 h = alerta; maré 2,3 m sobe; histórico de 14 sobe: crítico
    assert i1["classe_alagamento"] == "critico" and i1["nivel"] == "bairro"
    assert i1["classe_deslizamento"] != "sem_dados"
    assert i1["estagio_sugerido"] == "critico" and i1["confianca"] == "media"
    assert any("14 atendimentos de alagamento desde 2020" in m for m in i1["motivos"])
    # bairro sem histórico: alerta por chuva e maré (sobe para crítico), mas deslizamento sem dados
    assert i3["classe_alagamento"] == "critico"
    assert i3["classe_deslizamento"] == "sem_dados"
    assert i3["confianca"] == "baixa"
    assert "sem histórico de deslizamento na base" in i3["motivos"]
    assert 1 <= len(i3["motivos"]) <= 3
    # nenhum campo de probabilidade
    assert "%" not in str(corpo["dados"]["itens"]) and "probabilidade" not in str(corpo["dados"]["itens"])
    distrito = _item(corpo, i1["distrito_id"])
    assert distrito["nivel"] == "distrito" and distrito["classe_alagamento"] == "critico"
    assert sum(corpo["dados"]["resumo"]["por_classe"]["alagamento"].values()) == 94


def test_deslizamento_depende_do_historico_e_chuva_fraca_fica_em_observacao(equipe, sessao):
    b1, _, _ = _bairros(sessao)
    _carga(sessao, [(b1, "alagamento", 0), (b1, "deslizamento", 1)])
    fraca = {**PREMISSAS, "chuva_prevista_mm": 5, "chuva_acumulada_mm": 0, "mare_m": 0.1}
    i = _item(equipe["leitor"].post(f"{API}/simular", json=fraca).json(), b1)
    assert i["classe_alagamento"] == "observacao" and i["classe_deslizamento"] == "observacao"
    assert i["estagio_sugerido"] == "observacao"


def test_validacao_dos_limites(equipe):
    c = equipe["leitor"]
    for ruim in (
        {"chuva_prevista_mm": -1},
        {"chuva_prevista_mm": 5000},
        {"duracao_h": 0},
        {"duracao_h": 96},
        {"mare_m": 40},
        {"horizonte_h": 0},
    ):
        assert c.post(f"{API}/simular", json={**PREMISSAS, **ruim}).status_code == 422, ruim
    assert (
        c.post(f"{API}/simular", json={**PREMISSAS, "duracao_h": 48}).status_code == 422
    )  # passa do horizonte
    sem_campo = {k: v for k, v in PREMISSAS.items() if k != "mare_m"}
    assert c.post(f"{API}/simular", json=sem_campo).status_code == 422


def test_simulacao_exige_login(equipe, sessao):
    anonimo = cliente(sessao, equipe["relogio"])
    assert anonimo.post(f"{API}/simular", json=PREMISSAS).status_code == 401
    assert anonimo.get(f"{API}/premissas-atuais").status_code == 401


def test_desempenho_94_bairros_e_8_distritos_em_menos_de_2s(equipe, sessao):
    b = _bairros(sessao, 94)
    _carga(sessao, [(x, "alagamento", 2) for x in b[:40]] + [(x, "deslizamento", 1) for x in b[:20]])
    c = equipe["leitor"]
    c.post(f"{API}/simular", json=PREMISSAS)  # aquece o cache dos insumos estáticos
    r = c.post(f"{API}/simular", json=PREMISSAS).json()
    assert r["dados"]["tempo_calculo_ms"] < 2000
    assert len(r["dados"]["itens"]) == 102


# ------------------------------------------------------------------ premissas atuais
def test_premissas_atuais_sem_fontes_sao_nulas_e_dizem_quais_faltam(equipe):
    r = equipe["leitor"].get(f"{API}/premissas-atuais")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["dados"]["chuva_prevista_mm"] is None and d["dados"]["mare_m"] is None
    assert d["dados"]["chuva_acumulada_mm"] is None
    assert d["dados"]["horizonte_h"] == 24
    assert d["meta"]["dados_insuficientes"] is True
    ids = {f["id"] for f in d["meta"]["fontes"]}
    assert {"open-meteo-previsao", "open-meteo-mare", "apac-chuva"} <= ids


def test_premissas_atuais_com_fontes(equipe, sessao):
    relogio = equipe["relogio"]
    inicio = relogio.agora.replace(minute=0, second=0, microsecond=0)
    ex = sessao.execute(
        text(
            "insert into app.etl_execucoes (fonte_id, status, fim) values ('apac-chuva', 'sucesso', now()) returning id"
        )
    ).scalar_one()
    hoje = relogio.agora.date()
    for k in range(3):
        sessao.execute(
            text(
                "insert into gold.chuva_apac_diaria (territorio_id, dia, nivel, max_mm, n_estacoes) "
                "values ('ds-1', :d, 'distrito', 10, 2)"
            ),
            {"d": hoje.fromordinal(hoje.toordinal() - k)},
        )
    del ex
    c = equipe["leitor"]
    d = c.get(f"{API}/premissas-atuais").json()["dados"]
    assert d["chuva_acumulada_mm"] == 30.0
    # dois dias medidos não bastam: não vira número
    sessao.execute(text("delete from gold.chuva_apac_diaria where dia = :d"), {"d": hoje})
    assert c.get(f"{API}/premissas-atuais").json()["dados"]["chuva_acumulada_mm"] is None
    assert inicio


# ------------------------------------------------------------------ salvar, listar e abrir
def test_salvar_recalcula_no_servidor_audita_e_abre(equipe, sessao):
    b1, _, _ = _bairros(sessao)
    _carga(sessao, [(b1, "alagamento", 5)])
    r = equipe["analista"].post(
        f"{API}",
        json={"nome": "  Chuva   forte DS 1 ", "premissas": PREMISSAS, "resultado": {"itens": ["falso"]}},
    )
    assert r.status_code == 201, r.text
    d = r.json()["dados"]
    assert d["nome"] == "Chuva forte DS 1" and d["autor_nome"] == "Analista"
    assert len(d["resultado"]["itens"]) == 102  # o "resultado" enviado foi ignorado
    assert d["premissas"]["chuva_prevista_mm"] == 72
    assert d["resultado"]["fontes"][0]["id"] == "recife-alagamento"
    assert (
        sessao.execute(text("select count(*) from app.auditoria where acao = 'cenario_salvo'")).scalar() == 1
    )

    lista = equipe["leitor"].get(API).json()["dados"]
    assert [x["nome"] for x in lista] == ["Chuva forte DS 1"]
    assert lista[0]["autor_nome"] == "Analista" and lista[0]["resumo"]["por_classe"]["alagamento"]
    assert "resultado" not in lista[0]

    aberto = equipe["outra"].get(f"{API}/{d['id']}").json()
    assert aberto["dados"]["resultado"]["itens"] == d["resultado"]["itens"]
    assert aberto["meta"]["avisos"][0].startswith("Resultado calculado em")


def test_salvar_valida_nome_e_permissao_e_nao_existe_cenario(equipe):
    r = equipe["analista"].post(f"{API}", json={"nome": "   ", "premissas": PREMISSAS})
    assert r.status_code == 422
    assert (
        equipe["analista"].post(f"{API}", json={"nome": "x" * 121, "premissas": PREMISSAS}).status_code == 422
    )
    assert equipe["analista"].post(f"{API}", json={"nome": "ok"}).status_code == 422
    assert equipe["analista"].get(f"{API}/00000000-0000-0000-0000-000000000000").status_code == 404
    assert equipe["analista"].get(f"{API}/nao-e-uuid").status_code == 422


def test_cenario_salvo_nao_pode_ser_alterado_nem_apagado(equipe, sessao):
    d = equipe["analista"].post(f"{API}", json={"nome": "A", "premissas": PREMISSAS}).json()["dados"]
    for sql in (
        "update app.cenarios set nome = 'B'",
        "delete from app.cenarios",
        "truncate app.cenarios",
    ):
        with pytest.raises(DBAPIError), sessao.begin_nested():
            sessao.execute(text(sql))
    assert d["id"]


def test_rota_antiga_passou_para_estimativa(equipe):
    r = equipe["leitor"].get(f"{API}/estimativa", params={"territorio_id": "ds-3", "horizonte_h": 24})
    assert r.status_code == 200
    assert r.json()["dados"]["estimativa"]["experimental"] is True


def test_premissas_nulas_sao_aceitas_e_nao_viram_zero(equipe, sessao):
    b1, _, _ = _bairros(sessao)
    _carga(sessao, [(b1, "alagamento", 2), (b1, "deslizamento", 2)])
    c = equipe["leitor"]
    nulas = {**PREMISSAS, "chuva_acumulada_mm": None, "mare_m": None}
    r = c.post(f"{API}/simular", json=nulas)
    assert r.status_code == 200, r.text
    corpo = r.json()
    i = _item(corpo, b1)
    assert i["confianca"] == "baixa"
    assert "sem chuva acumulada informada" in i["motivos"]
    # 72 mm em 24 h = alerta; sem maré não sobe pela maré
    assert i["classe_alagamento"] != "sem_dados"
    assert corpo["meta"]["fonte_por_premissa"]["mare_m"] == "open-meteo-mare"
    # campos obrigatórios continuam obrigatórios
    for k in ("chuva_prevista_mm", "duracao_h", "horizonte_h"):
        assert c.post(f"{API}/simular", json={**PREMISSAS, k: None}).status_code == 422, k


def test_salvar_aceita_premissas_nulas(equipe):
    nulas = {**PREMISSAS, "chuva_acumulada_mm": None, "mare_m": None}
    r = equipe["analista"].post(f"{API}", json={"nome": "Sem insumos", "premissas": nulas})
    assert r.status_code == 201, r.text
    assert r.json()["dados"]["premissas"]["chuva_acumulada_mm"] is None
    assert r.json()["meta"]["fonte_por_premissa"]["chuva_acumulada_mm"] == "apac-chuva"


def test_premissas_atuais_devolve_fonte_por_premissa(equipe):
    m = equipe["leitor"].get(f"{API}/premissas-atuais").json()["meta"]["fonte_por_premissa"]
    assert m == {
        "chuva_prevista_mm": "open-meteo-previsao",
        "duracao_h": "open-meteo-previsao",
        "chuva_acumulada_mm": "apac-chuva",
        "mare_m": "open-meteo-mare",
    }


# ------------------------------------------------------------------ arboviroses como contexto do cenário
def _carga_saude(sessao, semanas: list[tuple[str, int, int | None]], por_bairro: dict[str, int]) -> None:
    """Dados de exemplo só no teste: casos semanais do município e confirmados do ano por bairro."""
    ex = sessao.execute(
        text(
            "insert into app.etl_execucoes (fonte_id, status, fim) values ('infodengue', 'sucesso', now()) returning id"
        )
    ).scalar_one()
    for agravo, semana, casos in semanas:
        sessao.execute(
            text(
                "insert into silver.infodengue_semanal (agravo, ano, semana, inicio, casos, nivel, incompleta, "
                "coletado_em, execucao_id) values (:a, 2026, :s, date '2026-01-04' + (:s - 1) * 7, :c, 2, false, now(), :e)"
            ),
            {"a": agravo, "s": semana, "c": casos, "e": ex},
        )
        sessao.execute(
            text(
                "insert into gold.saude_semanal (agravo, fonte_id, ano, semana, inicio, casos, incompleta) "
                "values (:a, 'infodengue', 2026, :s, date '2026-01-04' + (:s - 1) * 7, :c, false)"
            ),
            {"a": agravo, "s": semana, "c": casos},
        )
    ex2 = sessao.execute(
        text(
            "insert into app.etl_execucoes (fonte_id, status, fim) "
            "values ('recife-arboviroses', 'sucesso', now()) returning id"
        )
    ).scalar_one()
    for bairro, confirmados in por_bairro.items():
        sessao.execute(
            text(
                "insert into silver.arboviroses_bairro_ano (agravo, ano, bairro_fonte, territorio_id, notificados, "
                "confirmados, descartados, outros, execucao_id) values ('dengue', 2025, :b, :b, :c, :c, 0, 0, :e)"
            ),
            {"b": bairro, "c": confirmados, "e": ex2},
        )
        sessao.execute(
            text(
                "insert into gold.arboviroses_bairro_ano (agravo, ano, bairro_id, distrito_id, casos, notificados) "
                "select 'dengue', 2025, id, pai_id, :c, :c from app.territorios where id = :b"
            ),
            {"b": bairro, "c": confirmados},
        )


def _distrito_do(sessao, bairro: str) -> str:
    return sessao.execute(
        text("select pai_id from app.territorios where id = :b"), {"b": bairro}
    ).scalar_one()


def test_arboviroses_sem_fonte_dizem_dados_insuficientes_e_a_fonte_que_falta(equipe):
    corpo = equipe["leitor"].post(f"{API}/simular", json=PREMISSAS).json()
    ds = next(i for i in corpo["dados"]["itens"] if i["nivel"] == "distrito")
    arbo = {a["agravo"]: a for a in ds["arboviroses"]["agravos"]}
    assert set(arbo) == {"dengue", "chikungunya", "zika"}
    assert ds["arboviroses"]["classe_impacto"] is None  # ausência não é risco baixo (RN-01)
    for a in arbo.values():
        assert a["dados_insuficientes"] is True and a["classe_impacto"] is None
        assert a["semana_recente"] is None and a["serie_semanal"] == [] and a["casos_ano_distrito"] is None
    assert "falta a fonte infodengue" in arbo["dengue"]["motivo"]
    assert "falta a fonte recife-arboviroses" in arbo["dengue"]["motivo"]
    assert "zika" in arbo["zika"]["motivo"] and "Dados insuficientes" in arbo["zika"]["motivo"]
    assert all(i["arboviroses"] is None for i in corpo["dados"]["itens"] if i["nivel"] == "bairro")


def test_arboviroses_contexto_serie_supressao_classe_e_selo(equipe, sessao):
    por_ds = {}
    for b in _bairros(sessao, 94):
        por_ds.setdefault(_distrito_do(sessao, b), b)
    (d1, b1), (d2, b2), (d3, b3), (d4, b4) = list(por_ds.items())[:4]
    # semanas 32 a 41 de 2026 (agosto a outubro): recentes o bastante para valer (a série parada não vale)
    semanas = [("dengue", s + 31, 40 + s) for s in range(1, 11)] + [
        ("chikungunya", 41, 3),
        ("dengue", 42, None),
    ]
    _carga_saude(sessao, semanas, {b1: 30, b2: 3, b4: 10})
    r = equipe["leitor"].post(f"{API}/simular", json=PREMISSAS)
    assert r.status_code == 200, r.text
    corpo = r.json()
    ds = {i["territorio_id"]: i for i in corpo["dados"]["itens"] if i["nivel"] == "distrito"}
    dengue = {a["agravo"]: a for a in ds[d1]["arboviroses"]["agravos"]}["dengue"]
    # semana mais recente COM dado: a 11 (casos nulos) não vale como zero
    assert dengue["semana_recente"]["semana"] == 41 and dengue["semana_recente"]["casos"] == 50
    assert [p["semana"] for p in dengue["serie_semanal"]] == [35, 36, 37, 38, 39, 40, 41, 42]
    assert dengue["serie_semanal"][-1]["casos"] is None and dengue["serie_semanal"][-1]["suprimido"] is False
    assert dengue["ano_distrito"] == 2025 and dengue["casos_ano_distrito"] == 30
    assert dengue["classe_impacto"] == "alta" and dengue["dados_insuficientes"] is False
    assert ds[d1]["arboviroses"]["agravos_em_destaque"] == ["dengue"]
    # 1 a 4 casos: suprimido (RN-13); zero medido continua zero (RN-02)
    pequeno = {a["agravo"]: a for a in ds[d2]["arboviroses"]["agravos"]}["dengue"]
    assert pequeno["casos_ano_distrito"] is None and pequeno["casos_ano_suprimido"] is True
    assert pequeno["classe_impacto"] == "baixa"  # menor terço entre os distritos com casos
    media = {a["agravo"]: a for a in ds[d4]["arboviroses"]["agravos"]}["dengue"]
    assert media["classe_impacto"] == "media" and media["casos_ano_distrito"] == 10
    zero = {a["agravo"]: a for a in ds[d3]["arboviroses"]["agravos"]}["dengue"]
    assert zero["casos_ano_distrito"] == 0 and zero["casos_ano_suprimido"] is False
    chik = {a["agravo"]: a for a in ds[d1]["arboviroses"]["agravos"]}["chikungunya"]
    assert chik["semana_recente"]["casos"] is None and chik["semana_recente"]["suprimido"] is True
    # chikungunya sem fonte anual: sem classe, e diz qual fonte falta
    assert chik["classe_impacto"] is None and "recife-arboviroses" in chik["motivo"]
    # contexto, selo experimental e sem percentual (RN-06, RN-11)
    res = corpo["dados"]["resumo"]["arboviroses"]
    assert res["experimental"] is True and res["contexto"] is True
    assert "CONTEXTO" in res["aviso"] and "não previsão causal da chuva" in res["aviso"]
    assert res["granularidade_semanal"] == "municipio" and res["granularidade_anual"] == "distrito"
    assert {f["id"] for f in res["fontes"]} == {"infodengue", "recife-arboviroses"}
    assert all(f["atualizado_em"] for f in res["fontes"])  # fonte e hora (RF-19)
    assert {"infodengue", "recife-arboviroses"} <= {f["id"] for f in corpo["meta"]["fontes"]}
    assert corpo["dados"]["experimental"] is True and "%" not in str(ds[d1]["arboviroses"])
    ordem = corpo["dados"]["resumo"]["ordem_de_atencao_distritos"]
    assert len(ordem) == 8 and {o["distrito_id"] for o in ordem} == set(ds)
    primeiros = [o for o in ordem if o["estagio_sugerido"] == ordem[0]["estagio_sugerido"]]
    assert primeiros[0]["classe_arboviroses"] == "alta"  # empate de estágio: o de classe maior vem antes


def test_cenario_salvo_guarda_o_bloco_de_arboviroses(equipe):
    r = equipe["analista"].post(f"{API}", json={"nome": "Com contexto", "premissas": PREMISSAS})
    assert r.status_code == 201, r.text
    ds = next(i for i in r.json()["dados"]["resultado"]["itens"] if i["nivel"] == "distrito")
    assert len(ds["arboviroses"]["agravos"]) == 3
