"""Desempenho contra banco remoto (cache, consultas consolidadas, sessão enxuta) e saúde só com dado útil:
janela de leptospirose com declaração vigente, `utilizavel` por indicador e zika como "Dados insuficientes"."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import event, text

from climasense.etl import frescor
from climasense.infra import cache
from climasense.infra.postgres import _ping_se_ociosa, em_paralelo
from climasense.servicos import cenarios, decisao, saude_agravos
from climasense.servicos import fontes as servico_fontes
from climasense.territorio import carga
from tests.conftest import precisa_postgres
from tests.integration.apoio import Relogio, cliente, criar_conta, entrar

pytestmark = [precisa_postgres, pytest.mark.integracao]
API = "/api/v1"
AGORA = datetime(2026, 11, 5, 15, 0, tzinfo=UTC)


@pytest.fixture
def equipe(sessao):
    carga.sincronizar_territorios(sessao, carga.geo_local())
    relogio = Relogio()
    criar_conta(sessao, "ana@recife.pe.gov.br", ["analista"])
    c = cliente(sessao, relogio)
    assert entrar(c, "ana@recife.pe.gov.br").status_code == 200
    return c, relogio


def _contar_consultas(alvo):
    consultas: list[str] = []

    def antes(conn, cursor, statement, *a):
        consultas.append(statement)

    event.listen(alvo, "before_cursor_execute", antes)
    return consultas, lambda: event.remove(alvo, "before_cursor_execute", antes)


# ------------------------------------------------------------------ cache das fontes (RF-19)
def test_fontes_em_cache_nao_repetem_consulta_e_mantem_hora_da_ultima_carga(sessao, monkeypatch):
    monkeypatch.setattr(cache, "ativo", True)
    sessao.execute(
        text("insert into app.etl_execucoes (fonte_id, status, fim) values ('apac-chuva', 'sucesso', :f)"),
        {"f": AGORA - timedelta(minutes=10)},
    )
    sessao.flush()
    primeira = servico_fontes.meta(sessao, "apac-chuva", AGORA)
    consultas, parar = _contar_consultas(sessao.get_bind())
    try:
        segunda = servico_fontes.meta(sessao, "apac-chuva", AGORA)
        outra = servico_fontes.meta(sessao, "infodengue", AGORA)
    finally:
        parar()
    assert consultas == []  # as duas leituras saíram da memória
    assert segunda == primeira and primeira.atualizado_em == AGORA - timedelta(minutes=10)
    assert outra.id == "infodengue"
    # o selo é recalculado com o `agora` de cada pedido: o cache não deixa o dado "novo" para sempre
    mais_tarde = servico_fontes.meta(sessao, "apac-chuva", AGORA + timedelta(hours=3))
    assert mais_tarde.desatualizado is True and primeira.desatualizado is False
    assert mais_tarde.atualizado_em == primeira.atualizado_em


def test_fontes_estaticas_nunca_ficam_desatualizadas_pela_idade_da_carga(sessao):
    sessao.execute(
        text(
            "insert into app.etl_execucoes (fonte_id, status, fim) "
            "values ('ibge-censo-2022-bairro', 'sucesso', :f)"
        ),
        {"f": AGORA - timedelta(days=900)},
    )
    linha = next(f for f in servico_fontes.linhas(sessao, AGORA) if f["id"] == "ibge-censo-2022-bairro")
    assert linha["status"] == "atualizada"


def test_limites_de_fonte_de_carga_rara_seguem_a_cadencia_real():
    horas = frescor.limite_frescor_h
    assert horas("recife-arboviroses") >= 365 * 24  # anual
    assert horas("recife-areas-risco") >= 365 * 24
    assert horas("cnes-equipamentos") >= 31 * 24  # mensal
    assert horas("recife-alagamento") >= 60 * 24
    # fonte viva não foi afrouxada
    assert (horas("apac-chuva"), horas("alertas-oficiais"), horas("open-meteo-previsao")) == (1, 1, 6)
    assert horas("open-meteo-mare") == 24
    # sem dado continua sendo "sem resposta", nunca "em dia" nem "desatualizado"
    assert frescor.esta_desatualizado("recife-arboviroses", None, AGORA) is None


# ------------------------------------------------------------------ consultas consolidadas
def _semear_previsao(sessao, ds: str, emissoes: int, inicio: datetime):
    ex = sessao.execute(
        text(
            "insert into app.etl_execucoes (fonte_id, status, fim) "
            "values ('open-meteo-previsao', 'sucesso', now()) returning id"
        )
    ).scalar_one()
    for e in range(emissoes):
        for h in range(6):
            sessao.execute(
                text(
                    "insert into silver.observacoes (fonte_id, territorio_id, variavel, valor, unidade, tipo, "
                    "observado_em, emitido_em, coletado_em, execucao_id) values ('open-meteo-previsao', :t, "
                    "'chuva_mm', :v, 'mm', 'prevista', :o, :e, :e, :x)"
                ),
                {
                    "t": ds,
                    "v": None if (ds == "ds-2" and h == 3) else float(e + h),
                    "o": inicio + timedelta(hours=h),
                    "e": inicio - timedelta(hours=e + 1),
                    "x": ex,
                },
            )


def _limpar_observacoes(sessao):
    sessao.execute(
        text(
            "delete from silver.observacoes where fonte_id in ('open-meteo-previsao', 'open-meteo-historico')"
        )
    )


def test_previsao_consolidada_e_igual_a_de_cada_distrito(sessao):
    carga.sincronizar_territorios(sessao, carga.geo_local())
    _limpar_observacoes(sessao)
    inicio = AGORA.replace(minute=0)
    _semear_previsao(sessao, "ds-1", 6, inicio)  # 6 emissões: só as 4 últimas entram
    _semear_previsao(sessao, "ds-2", 2, inicio)  # com uma hora nula (RN-02)
    lote = cenarios.previsao_por_emissao_distritos(sessao, ["ds-1", "ds-2", "ds-3"], inicio)
    for ds in ("ds-1", "ds-2", "ds-3"):
        assert lote.get(ds, {}) == cenarios.previsao_por_emissao(sessao, ds, inicio)
    assert len(lote["ds-1"]) == 4 and "ds-3" not in lote  # sem previsão: ausente, não zero
    assert any(v is None for _, v in next(iter(lote["ds-2"].values())))


def test_chuva_horaria_consolidada_e_igual_a_de_cada_distrito(sessao):
    carga.sincronizar_territorios(sessao, carga.geo_local())
    _limpar_observacoes(sessao)
    inicio = AGORA.replace(minute=0)
    _semear_previsao(sessao, "ds-1", 2, inicio - timedelta(hours=6))
    _semear_previsao(sessao, "ds-2", 1, inicio - timedelta(hours=6))
    desde = inicio - timedelta(hours=24)
    lote = decisao.chuva_horaria_recente_distritos(sessao, ["ds-1", "ds-2", "ds-3"], desde, inicio)
    for ds in ("ds-1", "ds-2", "ds-3"):
        assert lote[ds] == decisao.chuva_horaria_recente(sessao, ds, desde, inicio)


def test_em_paralelo_sem_engine_roda_em_sequencia_na_mesma_sessao(sessao):
    # a sessão de teste está ligada a uma conexão (não a um Engine): nada de threads nem de outra conexão
    assert em_paralelo(sessao, [lambda s: s is sessao, lambda s: s is sessao]) == [True, True]
    assert em_paralelo(sessao, [lambda s: 1]) == [1]


def test_pre_ping_so_quando_a_conexao_ficou_ociosa():
    import time

    from sqlalchemy import exc

    from climasense.infra import postgres as pg

    class Cursor:
        def __init__(self, vivo):
            self.vivo, self.sql = vivo, []

        def execute(self, sql):
            if not self.vivo:
                raise RuntimeError("conexão caiu")
            self.sql.append(sql)

        def close(self):
            pass

    class Conexao:
        def __init__(self, vivo=True):
            self.cursor_ = Cursor(vivo)

        def cursor(self):
            return self.cursor_

        def rollback(self):
            pass

    registro = type("R", (), {"info": {}})()
    registro.info["ultimo_uso"] = time.monotonic()
    quente = Conexao()
    _ping_se_ociosa(quente, registro, None)
    assert quente.cursor_.sql == []  # em uso contínuo: sem ida e volta extra
    registro.info["ultimo_uso"] = time.monotonic() - pg.PING_APOS_OCIOSA_S - 1
    fria = Conexao()
    _ping_se_ociosa(fria, registro, None)
    assert fria.cursor_.sql == ["select 1"]
    with pytest.raises(exc.DisconnectionError):
        _ping_se_ociosa(Conexao(vivo=False), registro, None)


# ------------------------------------------------------------------ sessão enxuta
def _ultimo_uso(sessao):
    sessao.expire_all()
    return sessao.execute(
        text("select ultimo_uso from app.sessoes order by criada_em desc limit 1")
    ).scalar_one()


def test_renovacao_da_sessao_so_grava_a_cada_30_s_em_uso_continuo(equipe, sessao):
    c, relogio = equipe
    base = _ultimo_uso(sessao)
    relogio.avancar(seconds=10)
    assert c.get(f"{API}/estagios/oficial").status_code == 200
    assert _ultimo_uso(sessao) == base  # dentro de 30 s: não grava
    relogio.avancar(seconds=25)
    assert c.get(f"{API}/estagios/oficial").status_code == 200
    assert _ultimo_uso(sessao) == relogio.agora  # passou de 30 s: renova
    # a rota de sessão sempre renova (o contador de inatividade da tela depende dela)
    relogio.avancar(seconds=5)
    assert c.get(f"{API}/auth/eu").status_code == 200
    assert _ultimo_uso(sessao) == relogio.agora


def test_sessao_e_validada_uma_vez_por_requisicao_em_rota_auditada(equipe, sessao):
    c, _ = equipe
    consultas, parar = _contar_consultas(sessao.get_bind())
    try:
        assert c.get(f"{API}/saude/resumo").status_code == 200
    finally:
        parar()
    leituras = [q for q in consultas if "app.sessoes" in q and q.lstrip().upper().startswith("SELECT")]
    assert len(leituras) == 1
    n = sessao.execute(text("select count(*) from app.auditoria where acao = 'leitura_dados_saude'")).scalar()
    assert n == 1  # a auditoria de leitura continua gravando (RNF-01)


def test_sessao_revogada_ou_expirada_continua_barrada(equipe, sessao):
    c, relogio = equipe
    sessao.execute(text("update app.sessoes set revogada = true"))
    assert c.get(f"{API}/estagios/oficial").status_code == 401
    sessao.execute(text("update app.sessoes set revogada = false"))
    relogio.avancar(minutes=61)
    assert c.get(f"{API}/estagios/oficial").status_code == 401


# ------------------------------------------------------------------ janela de leptospirose
def _declarar(sessao, territorio, estagio, quando):
    autor = sessao.execute(text("select id from app.usuarios limit 1")).scalar_one()
    sessao.execute(
        text(
            "insert into app.estagio_declaracoes (territorio_id, estagio, justificativa, lote_id, autor_id, "
            "declarado_em) values (:t, :e, 'teste', :l, :a, :em)"
        ),
        {"t": territorio, "e": estagio, "l": uuid.uuid4(), "a": autor, "em": quando},
    )
    sessao.flush()


def _janela(c):
    return c.get(f"{API}/saude/resumo").json()["dados"]["janela_leptospirose"]


def test_janela_ignora_declaracao_encerrada(equipe, sessao):
    c, relogio = equipe
    _declarar(sessao, "ds-1", "critico", relogio.agora - timedelta(days=1))
    assert _janela(c)["ativa"] is True  # vigente: abre
    _declarar(sessao, "ds-1", "encerrado", relogio.agora - timedelta(hours=2))
    assert _janela(c) is None  # a equipe retirou a declaração: some


def test_encerrar_o_recife_retira_declaracao_de_distrito(equipe, sessao):
    c, relogio = equipe
    _declarar(sessao, "ds-4", "alerta", relogio.agora - timedelta(days=2))
    _declarar(sessao, "recife", "encerrado", relogio.agora - timedelta(days=1))
    assert _janela(c) is None
    _declarar(sessao, "ds-4", "alerta", relogio.agora - timedelta(hours=1))  # nova, depois do encerramento
    assert _janela(c)["ativa"] is True


def test_janela_antiga_demais_nao_e_mostrada(equipe, sessao):
    c, relogio = equipe
    _declarar(sessao, "ds-1", "critico", relogio.agora - timedelta(days=45))  # janela já encerrada
    assert _janela(c) is None
    _declarar(sessao, "ds-2", "alerta", relogio.agora - timedelta(days=20))
    assert _janela(c)["ativa"] is True


# ------------------------------------------------------------------ saúde só com dado útil
def _semana(sessao, agravo, fonte, inicio: date, casos):
    sessao.execute(
        text(
            "insert into gold.saude_semanal (agravo, fonte_id, ano, semana, inicio, casos, incompleta) "
            "values (:a, :f, :y, :w, :i, :c, false)"
        ),
        {
            "a": agravo,
            "f": fonte,
            "y": inicio.year,
            "w": inicio.timetuple().tm_yday // 7 + 1,
            "i": inicio,
            "c": casos,
        },
    )
    sessao.flush()


def test_semana_utilizavel_usa_o_fim_da_semana_contra_o_limite_da_fonte():
    # infodengue: limite 192 h = 8 dias
    assert saude_agravos.semana_utilizavel("infodengue", date(2026, 10, 25), AGORA)  # termina 31/10: 5 dias
    assert not saude_agravos.semana_utilizavel("infodengue", date(2026, 10, 18), AGORA)  # 24/10: 12 dias
    assert not saude_agravos.semana_utilizavel("infodengue", None, AGORA)
    # fonte sem limite definido não reprova por idade
    assert saude_agravos.semana_utilizavel("fonte-sem-limite", date(2020, 1, 5), AGORA)


def test_resumo_so_devolve_contagem_de_semana_utilizavel(equipe, sessao):
    c, _ = equipe  # relógio dos testes: 15/10/2026
    sessao.execute(text("delete from gold.saude_semanal"))
    _semana(sessao, "dengue", "infodengue", date(2026, 10, 11), 80)
    _semana(sessao, "chikungunya", "infodengue", date(2024, 2, 11), 7)  # a série parou em 2024
    r = c.get(f"{API}/saude/resumo").json()
    por = {a["agravo"]: a for a in r["dados"]["agravos"]}
    assert por["dengue"]["utilizavel"] is True and por["dengue"]["casos"] == 80
    assert por["dengue"]["ultima_semana_com_dado"]["inicio"] == "2026-10-11"
    assert por["dengue"]["motivo"] is None
    chik = por["chikungunya"]
    assert chik["utilizavel"] is False
    assert chik["casos"] is None and chik["ultima_semana"] is None and chik["variacao_4s_pct"] is None
    assert chik["ultima_semana_com_dado"]["inicio"] == "2024-02-11"
    assert chik["motivo"].startswith("Dados insuficientes") and "infodengue" in chik["motivo"]
    sem = por["leptospirose"]  # nenhuma semana: ausência, nunca zero
    assert sem["utilizavel"] is False and sem["ultima_semana_com_dado"] is None and sem["casos"] is None


def test_semana_com_casos_nulos_nao_e_a_ultima_com_dado(equipe, sessao):
    c, _ = equipe
    sessao.execute(text("delete from gold.saude_semanal"))
    _semana(sessao, "dengue", "infodengue", date(2026, 10, 4), 40)
    _semana(sessao, "dengue", "infodengue", date(2026, 10, 11), None)  # ainda não publicada
    d = {a["agravo"]: a for a in c.get(f"{API}/saude/resumo").json()["dados"]["agravos"]}["dengue"]
    assert d["ultima_semana_com_dado"]["inicio"] == "2026-10-04" and d["casos"] == 40


def test_semanal_de_zika_responde_dados_insuficientes_com_a_fonte(equipe):
    c, _ = equipe
    r = c.get(f"{API}/saude/semanal", params={"agravo": "zika"})
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["dados"]["agravo"] == "zika" and corpo["dados"]["itens"] == []
    assert corpo["dados"]["chuva"] == []
    assert "Dados insuficientes" in corpo["dados"]["motivo"] and "infodengue" in corpo["dados"]["motivo"]
    assert corpo["meta"]["dados_insuficientes"] is True
    assert c.get(f"{API}/saude/semanal", params={"agravo": "outra"}).status_code == 422


def test_cache_de_saude_nao_muda_o_resultado_e_expira(equipe, sessao, monkeypatch):
    c, _ = equipe
    sessao.execute(text("delete from gold.saude_semanal"))
    _semana(sessao, "dengue", "infodengue", date(2026, 10, 11), 80)
    sem_cache = c.get(f"{API}/saude/resumo").json()["dados"]["agravos"]
    monkeypatch.setattr(cache, "ativo", True)
    cache.limpar()
    com_cache = c.get(f"{API}/saude/resumo").json()["dados"]["agravos"]
    de_novo = c.get(f"{API}/saude/resumo").json()["dados"]["agravos"]
    assert sem_cache == com_cache == de_novo
    # a série mudou no banco: dentro do TTL o cache responde igual; vencido, recalcula
    sessao.execute(text("update gold.saude_semanal set casos = 99"))
    assert c.get(f"{API}/saude/resumo").json()["dados"]["agravos"] == com_cache
    cache.limpar("saude_semanal")
    novo = {a["agravo"]: a for a in c.get(f"{API}/saude/resumo").json()["dados"]["agravos"]}
    assert novo["dengue"]["casos"] == 99


def test_boletim_leva_utilizavel_por_indicador(equipe):
    c, _ = equipe
    r = c.get(f"{API}/boletim", params={"territorio_id": "recife"})
    assert r.status_code == 200, r.text
    assert all("utilizavel" in a and "ultima_semana_com_dado" in a for a in r.json()["dados"]["saude"])


# ------------------------------------------------------------------ Situação: chuva medida e série
def _apac_agora(sessao, ds, nivel, mm, n, atualizadas, lida, herdado=None):
    sessao.execute(
        text(
            "insert into gold.chuva_apac_agora (territorio_id, nivel, chuva_24h_max_mm, n_estacoes, n_atualizadas, "
            "lida_em, herdado_de, estacoes) values (:t, :n, :mm, :ne, :na, :l, :h, '{}')"
        ),
        {"t": ds, "n": nivel, "mm": mm, "ne": n, "na": atualizadas, "l": lida, "h": herdado},
    )


def test_situacao_chuva_por_distrito_maior_valor_e_estacoes_sem_leitura(equipe, sessao):
    c, relogio = equipe
    sessao.execute(text("delete from gold.chuva_apac_agora"))
    sessao.execute(text("delete from gold.chuva_apac_diaria"))
    lida = relogio.agora - timedelta(minutes=20)
    _apac_agora(sessao, "recife", "municipio", 55.0, 19, 17, lida)
    _apac_agora(sessao, "ds-1", "distrito", 12.0, 2, 2, lida)
    _apac_agora(sessao, "ds-2", "distrito", 55.0, 4, 3, lida)
    _apac_agora(sessao, "ds-3", "distrito", 8.0, 2, 2, relogio.agora - timedelta(hours=5))  # leitura velha
    _apac_agora(sessao, "ds-8", "distrito", 55.0, 19, 17, lida, herdado="recife")  # sem pluviômetro próprio
    hoje = relogio.agora.date()
    for ds, mm in (("ds-1", 10.0), ("ds-2", 30.0)):
        for d in range(3):
            sessao.execute(
                text(
                    "insert into gold.chuva_apac_diaria (territorio_id, dia, nivel, max_mm, mediana_mm, n_estacoes) "
                    "values (:t, :d, 'distrito', :mm, :mm, 2)"
                ),
                {"t": ds, "d": hoje - timedelta(days=d), "mm": mm},
            )
    sessao.execute(  # ds-3: só 2 dos 3 dias → 72 h indisponível (não é zero)
        text(
            "insert into gold.chuva_apac_diaria (territorio_id, dia, nivel, max_mm, mediana_mm, n_estacoes) "
            "values ('ds-3', :d, 'distrito', 5, 5, 2), ('ds-3', :e, 'distrito', 5, 5, 2)"
        ),
        {"d": hoje, "e": hoje - timedelta(days=1)},
    )
    sessao.flush()
    r = c.get(f"{API}/situacao/chuva")
    assert r.status_code == 200, r.text
    d = r.json()["dados"]
    por = {x["territorio_id"]: x for x in d["distritos"]}
    assert len(por) == 8
    assert por["ds-1"]["chuva_24h_mm"] == 12.0 and por["ds-1"]["chuva_72h_mm"] == 30.0
    assert (por["ds-2"]["estacoes_total"], por["ds-2"]["estacoes_sem_leitura"]) == (4, 1)
    assert d["maior_24h"] == {"territorio_id": "ds-2", "territorio_nome": "Distrito 2", "mm": 55.0}
    assert d["maior_72h"]["territorio_id"] == "ds-2" and d["maior_72h"]["mm"] == 90.0
    # leitura velha e distrito sem pluviômetro próprio: sem valor e com motivo, nunca zero
    assert por["ds-3"]["chuva_24h_mm"] is None and "Dados insuficientes" in por["ds-3"]["motivo"]
    assert por["ds-3"]["chuva_72h_mm"] is None
    assert por["ds-8"]["medicao_propria"] is False and por["ds-8"]["chuva_24h_mm"] is None
    assert por["ds-4"]["motivo"].startswith("Dados insuficientes")  # sem linha na fonte
    assert d["estacoes"] == {
        "total": 19,
        "com_leitura": 17,
        "sem_leitura": 2,
        "lida_em": d["estacoes"]["lida_em"],
    }
    assert set(d["previsao"]) >= {"chuva", "mare", "faixa_disponivel", "emissoes_na_faixa"}
    assert {f["id"] for f in r.json()["meta"]["fontes"]} == {
        "apac-chuva",
        "open-meteo-previsao",
        "open-meteo-mare",
    }


def test_situacao_chuva_sem_nenhuma_fonte_e_dados_insuficientes(equipe, sessao):
    c, _ = equipe
    sessao.execute(text("delete from gold.chuva_apac_agora"))
    sessao.execute(text("delete from silver.observacoes where fonte_id like 'open-meteo-%'"))
    d = c.get(f"{API}/situacao/chuva").json()
    assert d["dados"]["maior_24h"] is None and d["dados"]["maior_72h"] is None
    assert all(x["chuva_24h_mm"] is None for x in d["dados"]["distritos"])
    assert d["meta"]["dados_insuficientes"] is True


def test_situacao_chuva_em_cache_nao_muda_o_resultado_e_expira(equipe, sessao, monkeypatch):
    c, relogio = equipe
    sessao.execute(text("delete from gold.chuva_apac_agora"))
    _apac_agora(sessao, "ds-1", "distrito", 12.0, 2, 2, relogio.agora - timedelta(minutes=5))
    sessao.flush()
    antes = c.get(f"{API}/situacao/chuva").json()["dados"]
    monkeypatch.setattr(cache, "ativo", True)
    cache.limpar()
    primeira = c.get(f"{API}/situacao/chuva").json()["dados"]
    assert primeira == antes
    sessao.execute(text("update gold.chuva_apac_agora set chuva_24h_max_mm = 99"))
    assert c.get(f"{API}/situacao/chuva").json()["dados"] == primeira  # dentro do TTL
    cache.limpar("situacao_chuva")
    assert c.get(f"{API}/situacao/chuva").json()["dados"]["maior_24h"]["mm"] == 99.0


def test_situacao_chuva_exige_login(sessao):
    assert cliente(sessao, Relogio()).get(f"{API}/situacao/chuva").status_code == 401


# ------------------------------------------------------------------ distrito como "Distrito 5" nos textos da API
def test_textos_da_api_saem_com_distrito_em_numero(equipe, sessao):
    c, relogio = equipe
    nome = sessao.execute(text("select nome_exibicao from app.territorios where id = 'ds-5'")).scalar_one()
    assert "V" in nome  # o nome guardado no banco continua em romano
    r = c.post(
        f"{API}/estagios/mensagem",
        json={"territorio_ids": ["ds-5", "ds-8"], "estagio": "alerta", "justificativa": "Chuva no DS V"},
    )
    assert r.status_code == 200, r.text
    texto = r.json()["texto"]
    assert "Distrito 5" in texto and "Distrito 8" in texto
    assert "Sanitário" not in texto and "DS V" not in texto
    ds = {i["territorio_id"]: i for i in c.get(f"{API}/estagios").json()["dados"]["itens"]}
    assert ds["ds-5"]["territorio_nome"] == "Distrito 5" and ds["ds-5"]["territorio_id"] == "ds-5"
    b = c.get(f"{API}/boletim", params={"territorio_id": "ds-5"})
    assert b.json()["dados"]["territorio_nome"] == "Distrito 5"
    t = c.get(f"{API}/boletim/texto", params={"territorio_id": "recife"}).json()["texto"]
    assert "Sanitário" not in t and "DS " not in t


# ------------------------------------------------------------------ pendências da tela Situação
def _leitura(sessao, estacao, quando, janela, mm):
    ex = sessao.execute(
        text(
            "insert into app.etl_execucoes (fonte_id, status, fim) values ('apac-chuva', 'sucesso', now()) returning id"
        )
    ).scalar_one()
    sessao.execute(
        text(
            "insert into silver.apac_chuva_leituras (estacao_id, lida_em, janela_h, valor_mm, coletado_em, visto_em, "
            "execucao_id) values (:e, :l, :j, :v, :l, :l, :x)"
        ),
        {"e": estacao, "l": quando, "j": janela, "v": mm, "x": ex},
    )


def _estacao(sessao, id_, territorio):
    sessao.execute(
        text(
            "insert into silver.estacoes (id, fonte_id, codigo_fonte, nome, lat, lon, territorio_id) "
            "values (:i, 'apac-chuva', :i, :i, -8.05, -34.9, :t)"
        ),
        {"i": id_, "t": territorio},
    )


def test_situacao_serie_observada_e_72h_dos_pluviometros(equipe, sessao):
    c, relogio = equipe
    sessao.execute(text("delete from gold.chuva_apac_agora"))
    sessao.execute(text("delete from gold.chuva_apac_diaria"))
    sessao.execute(text("delete from silver.apac_chuva_leituras"))
    bairro = sessao.execute(
        text("select id from app.territorios where tipo='bairro' and pai_id='ds-2' limit 1")
    ).scalar()
    _estacao(sessao, "est-ds1", "ds-1")
    _estacao(sessao, "est-b2", bairro)  # estação em bairro: conta para o distrito do bairro
    agora = relogio.agora
    for estacao, mm in (("est-ds1", 4.0), ("est-b2", 9.5)):
        _leitura(sessao, estacao, agora - timedelta(minutes=10), 1, mm)
        _leitura(sessao, estacao, agora - timedelta(minutes=10), 72, mm * 10)
    _leitura(sessao, "est-ds1", agora - timedelta(hours=3, minutes=5), 1, 1.0)
    _leitura(
        sessao, "est-ds1", agora - timedelta(hours=3, minutes=25), 1, 2.0
    )  # última da hora anterior vale
    sessao.flush()
    d = c.get(f"{API}/situacao/chuva").json()["dados"]
    obs = d["observada"]
    assert obs["fonte"] == "apac-chuva" and obs["motivo"] is None
    horas = obs["serie"]
    assert horas == sorted(horas, key=lambda h: h["t"]) and len(horas) == 2
    assert horas[-1]["municipio_mm"] == 9.5 and horas[-1]["distritos"] == {"ds-1": 4.0, "ds-2": 9.5}
    assert horas[0]["distritos"] == {"ds-1": 1.0}  # hora sem leitura de outro distrito: lacuna, não zero
    por = {x["territorio_id"]: x for x in d["distritos"]}
    assert por["ds-1"]["chuva_72h_mm"] == 40.0 and por["ds-2"]["chuva_72h_mm"] == 95.0
    assert por["ds-1"]["fonte_chuva"] == "apac-chuva" and por["ds-4"]["fonte_chuva"] is None
    assert d["maior_72h"]["territorio_id"] == "ds-2"


def test_situacao_sem_leituras_diz_a_fonte_que_falta(equipe, sessao):
    c, _ = equipe
    sessao.execute(text("delete from silver.apac_chuva_leituras"))
    obs = c.get(f"{API}/situacao/chuva").json()["dados"]["observada"]
    assert obs["serie"] == [] and "Dados insuficientes" in obs["motivo"] and "apac-chuva" in obs["motivo"]


def test_chuva_24h_declara_apac_quando_ha_leitura_dos_pluviometros(equipe, sessao):
    c, relogio = equipe
    sessao.execute(text("delete from gold.chuva_apac_agora"))
    _apac_agora(sessao, "ds-1", "distrito", 12.0, 2, 2, relogio.agora - timedelta(minutes=5))
    sessao.flush()
    itens = {i["territorio_id"]: i for i in c.get(f"{API}/estagios").json()["dados"]["itens"]}
    ins = itens["ds-1"]["sugerido"]["insumos"]
    assert ins["chuva_24h_mm"] == 12.0 and ins["chuva_24h_fontes"] == ["apac-chuva"]
    assert itens["ds-2"]["sugerido"]["insumos"]["chuva_24h_fontes"] != [
        "apac-chuva"
    ]  # sem leitura: outra fonte


def test_estimativa_24h_devolve_faixa_minima_e_maxima_por_hora(equipe, sessao):
    c, relogio = equipe
    _limpar_observacoes(sessao)
    _semear_previsao(sessao, "ds-4", 3, relogio.agora.replace(minute=0, second=0, microsecond=0))
    for horizonte in (24, 72):
        r = c.get(f"{API}/cenarios/estimativa", params={"territorio_id": "ds-4", "horizonte_h": horizonte})
        assert r.status_code == 200, r.text
        chuva = r.json()["dados"]["chuva"]
        assert chuva and all(p["min"] is not None and p["max"] is not None for p in chuva)
        assert all(p["min"] <= p["valor"] <= p["max"] for p in chuva)
        assert any(p["min"] < p["max"] for p in chuva)


def test_cache_renovando_ignora_o_guardado_e_atualiza(monkeypatch):
    monkeypatch.setattr(cache, "ativo", True)
    cache.limpar()
    assert cache.obter("e", "k", 60, lambda: 1) == 1
    assert cache.obter("e", "k", 60, lambda: 2) == 1
    with cache.renovando():
        assert cache.obter("e", "k", 60, lambda: 3) == 3  # renova antes de vencer
    assert cache.obter("e", "k", 60, lambda: 4) == 3  # e o novo valor fica guardado
    cache.limpar()


def test_aquecimento_percorre_os_passos_sem_gravar_nada(sessao, equipe):
    import contextlib

    from climasense.servicos import aquecimento

    antes = sessao.execute(text("select count(*) from silver.previsoes_emitidas")).scalar()
    resultado = aquecimento.aquecer(lambda: contextlib.nullcontext(sessao), AGORA)
    assert resultado and all(resultado.values()), resultado
    assert sessao.execute(text("select count(*) from silver.previsoes_emitidas")).scalar() == antes
    assert aquecimento.INTERVALO_S < cache.VIVO_S
