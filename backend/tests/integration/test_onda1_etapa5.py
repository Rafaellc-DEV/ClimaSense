"""Onda 1, Etapa 5 (backend): situação do evento, ações por distrito e relatório executivo, painel antigo
removido (RF-08, RF-09, RF-15, RF-16, RF-17, RF-22). Dados de exemplo só aqui, nunca no produto."""

from __future__ import annotations

import pytest

from tests.conftest import precisa_postgres
from tests.integration.test_evento_chuva import API, _bairro_de, equipe  # noqa: F401

pytestmark = [precisa_postgres, pytest.mark.integracao]


def _situacao(c) -> dict:
    r = c.get(f"{API}/abrigos/situacao")
    assert r.status_code == 200, r.text
    return r.json()


def _ds(corpo: dict, ds: str) -> dict:
    return next(d for d in corpo["dados"]["distritos"] if d["distrito_id"] == ds)


def test_situacao_do_evento_sem_registro_nao_vira_zero(equipe):  # noqa: F811
    corpo = _situacao(equipe["ana"])
    cidade = corpo["dados"]["cidade"]
    assert cidade["abrigos_abertos"] is None and cidade["pessoas_abrigadas"] is None
    assert cidade["desabrigados"] is None and cidade["atualizado_em"] is None
    assert len(corpo["dados"]["distritos"]) == 8 and _ds(corpo, "ds-4")["desabrigados"] is None
    assert corpo["meta"]["dados_insuficientes"] is True
    ids = {f["id"] for f in corpo["meta"]["fontes"]}
    assert {"recife-abrigos", "recife-abrigos-ocupacao"} <= ids


def test_situacao_do_evento_parcial_total_e_historico(equipe, sessao):  # noqa: F811
    ana, cris = equipe["ana"], equipe["cris"]
    b4, b1 = _bairro_de(sessao, "ds-4"), _bairro_de(sessao, "ds-1")
    a = ana.post(f"{API}/abrigos", json={"nome": "Escola", "bairro_id": b4, "aberto": True}).json()
    ana.post(f"{API}/abrigos", json={"nome": "Ginásio", "bairro_id": b1, "aberto": False, "desabrigados": 7})

    c = _situacao(ana)["dados"]["cidade"]
    assert c["abrigos_abertos"] == 1 and c["parcial"] is True and c["abertos_sem_contagem"] == 1
    assert c["pessoas_abrigadas"] is None and c["desabrigados"] is None  # nunca soma subestimada

    r = cris.patch(f"{API}/abrigos/{a['id']}", json={"pessoas_abrigadas": 30, "desabrigados": 5})
    assert r.status_code == 200
    corpo = _situacao(ana)
    c = corpo["dados"]["cidade"]
    assert c["pessoas_abrigadas"] == 30 and c["desabrigados"] == 12 and c["parcial"] is False
    assert c["atualizado_por_nome"] == "Cris" and c["atualizado_em"]
    ds4, ds1 = _ds(corpo, "ds-4"), _ds(corpo, "ds-1")
    assert ds4["abrigos_abertos"] == 1 and ds4["pessoas_abrigadas"] == 30 and ds4["desabrigados"] == 5
    assert ds1["abrigos_abertos"] == 0 and ds1["pessoas_abrigadas"] == 0 and ds1["desabrigados"] == 7
    assert _ds(corpo, "ds-2")["abrigos_abertos"] is None  # sem abrigo cadastrado: ausente
    assert corpo["dados"]["ocupacao_atualizada_em"]
    ocupacao = next(f for f in corpo["meta"]["fontes"] if f["id"] == "recife-abrigos-ocupacao")
    assert ocupacao["atualizado_em"] and ocupacao["nome"].startswith("Registro da equipe")

    hist = ana.get(f"{API}/abrigos/{a['id']}/historico").json()
    assert hist[0]["pessoas_abrigadas"] == 30 and hist[0]["desabrigados"] == 5
    assert hist[0]["alteracoes"]["desabrigados"] == {"de": None, "para": 5}


def test_acoes_por_distrito_e_ordem_de_prioridade(equipe, sessao, monkeypatch):  # noqa: F811
    from climasense.servicos import acoes as servico_acoes

    ana = equipe["ana"]
    for ds, desc in (("ds-4", "Visita no DS IV"), ("ds-1", "Visita no DS I")):
        r = ana.post(
            f"{API}/acoes",
            json={
                "territorio_id": _bairro_de(sessao, ds),
                "tipo": "visita",
                "descricao": desc,
                "responsavel": "Equipe",
                "situacao": "em_andamento",
            },
        )
        assert r.status_code == 201, r.text
    monkeypatch.setattr(servico_acoes.prioridade_vulnerabilidade, "listar", lambda db, nivel=None: None)
    sem = ana.get(f"{API}/acoes", params={"situacao": "em_andamento", "ordem": "prioridade"}).json()
    assert sem["ordenado_por_prioridade"] is False and sem["total"] >= 2  # sem carga: ordem recente

    fake = {"itens": [{"territorio_id": "ds-1", "posicao": 1, "nome": "DS I"}], "desde": 2020}
    monkeypatch.setattr(servico_acoes.prioridade_vulnerabilidade, "listar", lambda db, nivel=None: fake)
    lista = ana.get(f"{API}/acoes", params={"situacao": "em_andamento", "ordem": "prioridade"}).json()
    assert lista["ordenado_por_prioridade"] is True
    assert [a["distrito_id"] for a in lista["itens"]][:2] == ["ds-1", "ds-4"]
    assert {d["distrito_id"]: d["contagens"] for d in lista["por_distrito"]}["ds-4"] == {"em_andamento": 1}
    assert ana.get(f"{API}/acoes", params={"ordem": "aleatoria"}).status_code == 422


def test_relatorio_executivo_no_boletim(equipe, sessao):  # noqa: F811
    ana = equipe["ana"]
    b4 = _bairro_de(sessao, "ds-4")
    assert ana.post(f"{API}/estagios/oficial", json={"estagio": "alerta"}).status_code == 201
    ana.post(
        f"{API}/abrigos",
        json={"nome": "Escola", "bairro_id": b4, "aberto": True, "pessoas_abrigadas": 20, "desabrigados": 9},
    )
    base = {"territorio_id": b4, "tipo": "visita", "responsavel": "Equipe DS IV"}
    ana.post(f"{API}/acoes", json={**base, "descricao": "Em curso", "situacao": "em_andamento"})
    assert (
        ana.post(f"{API}/acoes", json={**base, "descricao": "Feita", "situacao": "concluida"}).status_code
        == 201
    )

    r = ana.get(f"{API}/boletim")
    assert r.status_code == 200, r.text
    b, meta = r.json()["dados"], r.json()["meta"]
    assert b["estagio_oficial"]["estagio"] == "alerta" and b["periodo"]["desde"] <= b["periodo"]["ate"]
    assert b["abrigos"]["situacao"]["cidade"]["desabrigados"] == 9
    assert [a["descricao"] for a in b["acoes_concluidas"]] == ["Feita"]
    assert [a["descricao"] for a in b["acoes_em_andamento"]] == ["Em curso"]
    assert {d["distrito_id"]: d["contagens"] for d in b["acoes_por_distrito"]}["ds-4"] == {
        "em_andamento": 1,
        "concluida": 1,
    }
    assert {a["agravo"] for a in b["saude"]} == {"dengue", "chikungunya", "leptospirose"}
    ids = {f["id"] for f in meta["fontes"]}
    assert {"recife-abrigos-ocupacao", "cop-estagio-oficial", "infodengue"} <= ids

    texto = ana.get(f"{API}/boletim/texto").json()["texto"]
    assert "Estágio oficial do COP (cidade): Alerta" in texto
    assert "20 abrigado(s), 9 desabrigado(s)" in texto and "Ações concluídas no período" in texto
    assert ana.get(f"{API}/boletim", params={"desde": "2026-02-02", "ate": "2026-02-01"}).status_code == 422
    passado = ana.get(f"{API}/boletim", params={"desde": "2020-01-01", "ate": "2020-01-31"}).json()["dados"]
    assert passado["acoes_concluidas"] == []  # a ação concluída agora fica fora de um período antigo


def test_painel_antigo_removido_e_resumo_continua(equipe):  # noqa: F811
    ana = equipe["ana"]
    assert ana.get(f"{API}/painel/situacao").status_code == 404
    assert ana.get(f"{API}/painel/acoes").status_code == 404
    assert ana.get(f"{API}/painel/resumo").status_code == 200
