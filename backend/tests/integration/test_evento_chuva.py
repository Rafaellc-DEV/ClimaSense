"""Evento de chuva pela API, com Postgres real (specs/foco-chuvas.md F1–F5): estágio sugerido e declarado,
limiares com histórico, mensagem de WhatsApp, abrigos, ações e boletim."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from climasense.territorio import carga
from tests.conftest import precisa_postgres
from tests.integration.apoio import Relogio, cliente, criar_conta, entrar

pytestmark = [precisa_postgres, pytest.mark.integracao]
API = "/api/v1"


@pytest.fixture
def equipe(sessao):
    carga.sincronizar_territorios(sessao, carga.geo_local())
    relogio = Relogio()
    pessoas = {"relogio": relogio}
    for email, papeis in [("ana@recife.pe.gov.br", ["analista"]), ("cris@recife.pe.gov.br", ["coordenacao"])]:
        criar_conta(sessao, email, papeis, nome=email.split("@")[0].capitalize())
        c = cliente(sessao, relogio)
        entrar(c, email)
        pessoas[email.split("@")[0]] = c
    return pessoas


def _execucao(sessao, fonte: str) -> str:
    return str(
        sessao.execute(
            text(
                "insert into app.etl_execucoes (fonte_id, status, fim) values (:f, 'sucesso', now()) returning id"
            ),
            {"f": fonte},
        ).scalar_one()
    )


def _previsao_ds4_com_mare(sessao, agora):
    """Previsão real em forma (dados de teste, não do produto): 1,5 mm/h por 60 h, pico de 10 mm em +10 h,
    e maré de 0,8 m perto do pico. Só o DS IV tem previsão."""
    inicio = agora.replace(minute=0, second=0, microsecond=0)
    emitido = inicio - timedelta(hours=1)
    # outros testes deixam previsões gravadas; aqui elas somem só dentro da transação desfeita ao fim
    sessao.execute(
        text("delete from silver.observacoes where fonte_id in ('open-meteo-previsao', 'open-meteo-mare')")
    )
    ex = _execucao(sessao, "open-meteo-previsao")
    for h in range(60):
        sessao.execute(
            text(
                "insert into silver.observacoes (fonte_id, territorio_id, variavel, valor, unidade, tipo, observado_em, "
                "emitido_em, coletado_em, execucao_id) values ('open-meteo-previsao', 'ds-4', 'chuva_mm', :v, 'mm', "
                "'prevista', :t, :e, :e, :x)"
            ),
            {"v": 10.0 if h == 10 else 1.5, "t": inicio + timedelta(hours=h), "e": emitido, "x": ex},
        )
    ex = _execucao(sessao, "open-meteo-mare")
    for h in range(72):
        sessao.execute(
            text(
                "insert into silver.observacoes (fonte_id, territorio_id, variavel, valor, unidade, tipo, observado_em, "
                "emitido_em, coletado_em, execucao_id) values ('open-meteo-mare', null, 'mare_m', :v, 'm', 'prevista', "
                ":t, :e, :e, :x)"
            ),
            {"v": 0.8 if 9 <= h <= 11 else 0.2, "t": inicio + timedelta(hours=h), "e": emitido, "x": ex},
        )


def _bairro_de(sessao, ds: str) -> str:
    return sessao.execute(
        text("select id from app.territorios where pai_id = :d order by id limit 1"), {"d": ds}
    ).scalar_one()


def test_estagio_sugerido_por_distrito_e_bairro_herda(equipe, sessao):
    ana, relogio = equipe["ana"], equipe["relogio"]
    _previsao_ds4_com_mare(sessao, relogio.agora)
    r = ana.get(f"{API}/estagios")
    assert r.status_code == 200, r.text
    corpo = r.json()
    itens = {i["territorio_id"]: i for i in corpo["dados"]["itens"]}
    assert len(itens) == 8 and corpo["dados"]["parametros_versao"] is None
    ds4 = itens["ds-4"]["sugerido"]
    # 23 × 1,5 + 10 = 44,5 mm em 24 h → atenção; maré alta perto do pico → alerta
    assert ds4["insumos"]["chuva_prev_24h_mm"] == 44.5 and ds4["estagio"] == "alerta"
    assert (
        ds4["insumos"]["chuva_prev_72h_mm"] == pytest.approx(98.5)
        and ds4["insumos"]["horas_previstas_72h"] == 60
    )
    assert any("Maré alta" in m for m in ds4["motivos"])
    assert ds4["insumos"]["risco_ml"] is None  # modelo de ML não publicado: fora do cálculo
    assert itens["ds-4"]["alertas_oficiais"] == []  # reservado para o conector de alertas oficiais
    assert ds4["insumos"]["chuva_24h_mm"] is None and ds4["insumos"]["chuva_24h_fontes"] == []
    # sem previsão: sem dados, nunca observação (RN-01)
    assert itens["ds-1"]["sugerido"]["estagio"] == "sem_dados" and itens["ds-1"]["declarado"] is None
    assert any("APAC" in a for a in corpo["meta"]["avisos"])

    bairros = ana.get(f"{API}/estagios", params={"nivel": "bairro", "distrito_id": "ds-4"}).json()["dados"][
        "itens"
    ]
    assert bairros and all(b["herda_chuva_de"] == "ds-4" and b["nivel"] == "bairro" for b in bairros)
    assert all(b["sugerido"]["estagio"] == "alerta" for b in bairros)
    assert bairros[0]["sugerido"]["insumos"]["ocorrencias_historicas"] is None  # fonte sem carga ≠ zero


def test_declarar_estagio_auditado_e_herdado_pelos_bairros(equipe, sessao):
    ana, relogio = equipe["ana"], equipe["relogio"]
    _previsao_ds4_com_mare(sessao, relogio.agora)
    r = ana.post(
        f"{API}/estagios", json={"territorio_ids": ["ds-4"], "estagio": "alerta", "justificativa": "  "}
    )
    assert r.status_code == 422 and "justificativa" in r.json()["detail"]
    assert (
        ana.post(
            f"{API}/estagios", json={"territorio_ids": ["ds-4"], "estagio": "sem_dados", "justificativa": "x"}
        ).status_code
        == 422
    )
    assert (
        ana.post(
            f"{API}/estagios", json={"territorio_ids": ["ds-9"], "estagio": "alerta", "justificativa": "x"}
        ).status_code
        == 422
    )

    r = ana.post(
        f"{API}/estagios",
        json={
            "territorio_ids": ["ds-4"],
            "estagio": "critico",
            "justificativa": "COP confirmou alagamentos.",
        },
    )
    assert r.status_code == 201, r.text
    [d] = r.json()
    assert d["estagio"] == "critico" and d["autor_nome"] == "Ana" and d["sugerido_estagio"] == "alerta"

    itens = {i["territorio_id"]: i for i in ana.get(f"{API}/estagios").json()["dados"]["itens"]}
    dec = itens["ds-4"]["declarado"]
    assert dec["estagio"] == "critico" and dec["herdado"] is False
    assert itens["ds-4"]["sugerido"]["estagio"] == "alerta"  # a sugestão não muda com a declaração

    bairro = _bairro_de(sessao, "ds-4")
    b = {
        i["territorio_id"]: i
        for i in ana.get(f"{API}/estagios", params={"nivel": "bairro"}).json()["dados"]["itens"]
    }
    assert (
        b[bairro]["declarado"]["herdado"] is True and b[bairro]["declarado"]["territorio_origem_id"] == "ds-4"
    )

    relogio.avancar(minutes=10)
    ana.post(
        f"{API}/estagios", json={"territorio_ids": [bairro], "estagio": "alerta", "justificativa": "Bairro."}
    )
    hist = ana.get(f"{API}/estagios/historico", params={"territorio_id": "ds-4"}).json()
    assert [h["territorio_id"] for h in hist] == [
        bairro,
        "ds-4",
    ]  # distrito inclui os bairros, recente primeiro
    assert ana.get(f"{API}/estagios/historico", params={"desde": "2030-01-01"}).json() == []
    acoes = (
        sessao.execute(text("select acao from app.auditoria where acao = 'estagio_declarado'"))
        .scalars()
        .all()
    )
    assert len(acoes) == 2

    # histórico só aceita inclusões
    with pytest.raises(DBAPIError), sessao.begin_nested():
        sessao.execute(text("update app.estagio_declaracoes set estagio = 'observacao'"))


def test_limiares_so_coordenacao_altera_com_historico(equipe, sessao):
    ana, cris, relogio = equipe["ana"], equipe["cris"], equipe["relogio"]
    _previsao_ds4_com_mare(sessao, relogio.agora)
    atual = ana.get(f"{API}/estagios/parametros").json()
    assert atual["padrao"] is True and atual["limiares"]["chuva_prev_24h_atencao_mm"] == 25.0
    assert ana.put(f"{API}/estagios/parametros", json={"chuva_prev_24h_atencao_mm": 10}).status_code == 403

    r = cris.put(f"{API}/estagios/parametros", json={"chuva_prev_24h_atencao_mm": 80})
    assert r.status_code == 422 and "menor que o de alerta" in r.json()["detail"]
    assert cris.put(f"{API}/estagios/parametros", json={"limiar_inventado": 1}).status_code == 422

    novo = {**atual["limiares"], "chuva_prev_24h_alerta_mm": 40.0}
    r = cris.put(f"{API}/estagios/parametros", json={"limiares": novo, "justificativa": "Ajuste do piloto."})
    assert r.status_code == 200, r.text
    assert (
        r.json()["versao"] == 1 and r.json()["atualizado_por_nome"] == "Cris" and r.json()["padrao"] is False
    )
    ds4 = next(i for i in ana.get(f"{API}/estagios").json()["dados"]["itens"] if i["territorio_id"] == "ds-4")
    assert ds4["sugerido"]["estagio"] == "critico"  # 44,5 ≥ 40 → alerta; maré → crítico

    cris.put(f"{API}/estagios/parametros", json={"mare_alta_m": 0.9})  # só um campo, o resto se mantém
    hist = ana.get(f"{API}/estagios/parametros/historico").json()
    assert [h["versao"] for h in hist] == [2, 1]
    assert (
        hist[0]["limiares"]["chuva_prev_24h_alerta_mm"] == 40.0 and hist[0]["limiares"]["mare_alta_m"] == 0.9
    )


def test_mensagem_whatsapp_auditada_e_uso(equipe, sessao):
    ana = equipe["ana"]
    r = ana.post(
        f"{API}/estagios/mensagem",
        json={"territorio_ids": ["ds-4", "recife"], "estagio": "alerta", "justificativa": "Chuva forte."},
    )
    assert r.status_code == 200, r.text
    m = r.json()
    assert (
        "Estágio: *ALERTA*" in m["texto"]
        and "Recife inteiro" in m["texto"]
        and "Motivo: Chuva forte." in m["texto"]
    )
    assert m["wa_me_url"].startswith("https://wa.me/?text=")
    assert (
        ana.post(
            f"{API}/estagios/mensagem/uso", json={"evento": "copiar", "territorio_ids": ["ds-4"]}
        ).status_code
        == 204
    )
    assert (
        ana.post(
            f"{API}/estagios/mensagem/uso", json={"evento": "enviar", "territorio_ids": ["ds-4"]}
        ).status_code
        == 422
    )
    acoes = set(sessao.execute(text("select acao from app.auditoria where alvo_tipo = 'estagio'")).scalars())
    assert acoes == {"estagio_mensagem_gerada", "estagio_mensagem_copiada"}
    # nada declarado por gerar mensagem
    assert sessao.execute(text("select count(*) from app.estagio_declaracoes")).scalar() == 0


def test_abrigos_com_historico_totais_e_painel(equipe, sessao):
    ana, cris, relogio = equipe["ana"], equipe["cris"], equipe["relogio"]
    bairro = _bairro_de(sessao, "ds-4")
    assert ana.post(f"{API}/abrigos", json={"nome": "Escola", "bairro_id": "ds-4"}).status_code == 422
    r = ana.post(
        f"{API}/abrigos",
        json={
            "nome": "Escola Municipal",
            "bairro_id": bairro,
            "capacidade": 120,
            "aberto": True,
            "pessoas_abrigadas": 30,
        },
    )
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["origem"] == "manual" and a["latitude"] is None
    assert a["distrito_id"] == "ds-4" and a["atualizado_por_nome"] == "Ana" and a["desabrigados"] is None
    ana.post(
        f"{API}/abrigos", json={"nome": "Ginásio", "bairro_id": _bairro_de(sessao, "ds-1"), "aberto": False}
    )

    relogio.avancar(minutes=30)
    r = cris.patch(f"{API}/abrigos/{a['id']}", json={"pessoas_abrigadas": 55, "desabrigados": 70})
    assert r.status_code == 200 and r.json()["atualizado_por_nome"] == "Cris"
    assert cris.patch(f"{API}/abrigos/{a['id']}", json={"pessoas_abrigadas": -1}).status_code == 422
    assert (
        cris.patch(f"{API}/abrigos/{a['id']}", json={"latitude": -8.06}).status_code == 422
    )  # sem longitude
    r = cris.patch(f"{API}/abrigos/{a['id']}", json={"latitude": -8.06, "longitude": -34.9})
    assert r.json()["latitude"] == -8.06 and r.json()["longitude"] == -34.9

    hist = ana.get(f"{API}/abrigos/{a['id']}/historico").json()
    assert [h["autor_nome"] for h in hist] == ["Cris", "Cris", "Ana"]
    assert hist[0]["alteracoes"]["latitude"] == {"de": None, "para": -8.06}
    assert hist[1]["alteracoes"]["pessoas_abrigadas"] == {"de": 30, "para": 55}

    lista = ana.get(f"{API}/abrigos").json()
    t = lista["totais"]
    assert t["abrigos_abertos"] == 1 and t["pessoas_abrigadas"] == 55 and t["desabrigados"] == 70
    assert t["abrigos_cadastrados"] == 2 and len(lista["itens"]) == 2
    so_ds4 = ana.get(f"{API}/abrigos", params={"distrito_id": "ds-4", "aberto": "true"}).json()
    assert [x["id"] for x in so_ds4["itens"]] == [a["id"]]
    # pré-carga dos Dados Abertos (próxima onda) entra sem autor; manual sem autor é recusado no banco
    sessao.execute(
        text(
            "insert into app.abrigos (nome, bairro_id, origem, codigo_fonte, latitude, longitude) "
            "values ('Abrigo CKAN', :b, 'dados-abertos', 'ckan-1', -8.05, -34.88)"
        ),
        {"b": bairro},
    )
    with pytest.raises(DBAPIError), sessao.begin_nested():
        sessao.execute(
            text("insert into app.abrigos (nome, bairro_id) values ('Sem autor', :b)"), {"b": bairro}
        )
    ckan = next(x for x in ana.get(f"{API}/abrigos").json()["itens"] if x["origem"] == "dados-abertos")
    assert ckan["atualizado_por_nome"] is None and ckan["aberto"] is False
    painel = ana.get(f"{API}/painel/resumo").json()["abrigos"]
    assert painel["abrigos_abertos"] == 1 and painel["desabrigados"] == 70 and painel["atualizado_em"]


def test_acoes_linha_do_tempo_e_licao(equipe, sessao):
    ana, relogio = equipe["ana"], equipe["relogio"]
    bairro = _bairro_de(sessao, "ds-4")
    base = {"territorio_id": bairro, "tipo": "visita", "descricao": "Visita às famílias da beira do canal."}
    assert ana.post(f"{API}/acoes", json={**base, "tipo": "festa"}).status_code == 422
    r = ana.post(f"{API}/acoes", json={**base, "responsavel": "Equipe DS IV"})
    assert r.status_code == 201, r.text
    acao = r.json()
    assert (
        acao["situacao"] == "planejada" and acao["distrito_id"] == "ds-4" and len(acao["linha_do_tempo"]) == 1
    )

    assert ana.patch(f"{API}/acoes/{acao['id']}", json={"licao_aprendida": "cedo"}).status_code == 422
    relogio.avancar(minutes=15)
    r = ana.patch(f"{API}/acoes/{acao['id']}", json={"situacao": "em_andamento"})
    assert r.json()["inicio_em"] is not None
    em_andamento = ana.get(
        f"{API}/acoes", params={"territorio_id": "ds-4", "situacao": "em_andamento"}
    ).json()
    assert [x["id"] for x in em_andamento["itens"]] == [acao["id"]]

    relogio.avancar(minutes=50)  # a sessão expira com 60 min sem uso
    r = ana.patch(
        f"{API}/acoes/{acao['id']}",
        json={"situacao": "concluida", "licao_aprendida": "Avisar a escola antes."},
    )
    d = r.json()
    assert r.status_code == 200, r.text
    assert d["situacao"] == "concluida" and d["fim_em"] and d["licao_aprendida"] == "Avisar a escola antes."
    assert [e["situacao"] for e in d["linha_do_tempo"]] == ["planejada", "em_andamento", "concluida"]
    assert ana.patch(f"{API}/acoes/{acao['id']}", json={"situacao": "em_andamento"}).status_code == 409
    assert ana.patch(f"{API}/acoes/{acao['id']}", json={"descricao": "Outra."}).status_code == 409
    assert ana.get(f"{API}/acoes", params={"desde": "2030-01-01"}).json()["itens"] == []
    assert ana.get(f"{API}/acoes").json()["contagens"] == {"concluida": 1}


def test_boletim_consolida_e_resume_para_whatsapp(equipe, sessao):
    ana, relogio = equipe["ana"], equipe["relogio"]
    _previsao_ds4_com_mare(sessao, relogio.agora)
    bairro = _bairro_de(sessao, "ds-4")
    ana.post(
        f"{API}/abrigos", json={"nome": "Escola", "bairro_id": bairro, "aberto": True, "desabrigados": 12}
    )
    ana.post(
        f"{API}/acoes",
        json={
            "territorio_id": bairro,
            "tipo": "orientacao",
            "descricao": "Carro de som.",
            "situacao": "em_andamento",
        },
    )
    r = ana.get(f"{API}/boletim")
    assert r.status_code == 200, r.text
    b = r.json()["dados"]
    assert b["territorio_id"] == "recife" and len(b["estagios"]) == 8
    assert [t["territorio_id"] for t in b["territorios_em_atencao"]] == [
        "ds-4"
    ]  # bairros herdados não repetem
    assert b["chuva"]["chuva_prev_24h_mm"] == 44.5 and b["mare"]["maxima_m"] == 0.8
    assert b["abrigos"]["totais"]["abrigos_abertos"] == 1 and len(b["acoes_em_andamento"]) == 1

    so_ds1 = ana.get(f"{API}/boletim", params={"territorio_id": "ds-1"}).json()["dados"]
    assert [e["territorio_id"] for e in so_ds1["estagios"]] == ["ds-1"] and so_ds1["acoes_em_andamento"] == []

    t = ana.get(f"{API}/boletim/texto").json()
    assert "*Boletim ClimaSense · Vigidesastres*" in t["texto"] and "Ações em andamento: 1" in t["texto"]
    assert t["wa_me_url"].startswith("https://wa.me/?text=")


def test_encerrar_estagio_volta_a_sem_declaracao_e_guarda_o_historico(equipe, sessao):
    """Encerrar é uma nova linha no histórico (que é só de inclusão): o território deixa de mostrar o declarado,
    os bairros também, e nada foi apagado nem alterado."""
    ana, relogio = equipe["ana"], equipe["relogio"]
    _previsao_ds4_com_mare(sessao, relogio.agora)
    bairro = _bairro_de(sessao, "ds-4")
    ana.post(
        f"{API}/estagios",
        json={"territorio_ids": ["ds-4"], "estagio": "critico", "justificativa": "Testando o sistema."},
    )
    relogio.avancar(minutes=5)

    # sem justificativa não encerra, e a mensagem de WhatsApp não existe para "encerrado"
    assert (
        ana.post(
            f"{API}/estagios", json={"territorio_ids": ["ds-4"], "estagio": "encerrado", "justificativa": " "}
        ).status_code
        == 422
    )
    assert (
        ana.post(
            f"{API}/estagios/mensagem", json={"territorio_ids": ["ds-4"], "estagio": "encerrado"}
        ).status_code
        == 422
    )

    r = ana.post(
        f"{API}/estagios",
        json={"territorio_ids": ["ds-4"], "estagio": "encerrado", "justificativa": "Era só um teste."},
    )
    assert r.status_code == 201, r.text
    assert r.json()[0]["estagio"] == "encerrado" and r.json()[0]["rotulo"] == "Encerrado"

    itens = {i["territorio_id"]: i for i in ana.get(f"{API}/estagios").json()["dados"]["itens"]}
    assert itens["ds-4"]["declarado"] is None  # voltou a "sem declaração"; a sugestão do sistema continua
    assert itens["ds-4"]["sugerido"]["estagio"] == "alerta"
    b = {
        i["territorio_id"]: i
        for i in ana.get(f"{API}/estagios", params={"nivel": "bairro"}).json()["dados"]["itens"]
    }
    assert b[bairro]["declarado"] is None

    hist = ana.get(f"{API}/estagios/historico", params={"territorio_id": "ds-4"}).json()
    assert [h["estagio"] for h in hist] == ["encerrado", "critico"]  # nada foi apagado
    acoes = sessao.execute(text("select acao from app.auditoria where acao like 'estagio_%'")).scalars().all()
    assert "estagio_encerrado" in acoes and "estagio_declarado" in acoes

    # declarar de novo depois de encerrar vale normalmente
    relogio.avancar(minutes=5)
    ana.post(
        f"{API}/estagios",
        json={"territorio_ids": ["ds-4"], "estagio": "atencao", "justificativa": "Nova chuva."},
    )
    itens = {i["territorio_id"]: i for i in ana.get(f"{API}/estagios").json()["dados"]["itens"]}
    assert itens["ds-4"]["declarado"]["estagio"] == "atencao"
