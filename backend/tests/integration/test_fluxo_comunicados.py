"""T7.2–T7.6 e T6.6: o fluxo real de avaliações e comunicados pela API, até a landing."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import text

from climasense.servicos import fluxo
from climasense.territorio import carga
from tests.conftest import precisa_postgres
from tests.integration.apoio import Relogio, cliente, criar_conta, entrar

pytestmark = [precisa_postgres, pytest.mark.integracao]
API = "/api/v1"


@pytest.fixture
def equipe(sessao):
    carga.sincronizar_territorios(sessao, carga.geo_local())
    relogio = Relogio()
    pessoas = {}
    for email, papeis in [
        ("ana@recife.pe.gov.br", ["analista"]),
        ("rui@recife.pe.gov.br", ["revisor"]),
        ("cris@recife.pe.gov.br", ["coordenacao"]),
    ]:
        criar_conta(sessao, email, papeis, nome=email.split("@")[0].capitalize())
        c = cliente(sessao, relogio)
        entrar(c, email)
        pessoas[email.split("@")[0]] = c
    pessoas["publico"] = cliente(sessao, relogio)
    pessoas["relogio"] = relogio
    return pessoas


def _comunicado(relogio, **extra):
    base = {
        "territorios": ["bairro-afogados", "ds-5"],
        "publico": "populacao",
        "nivel": "alerta",
        "titulo": "Alerta de alagamento em Afogados",
        "texto": "Chuva forte prevista para a tarde, com maré alta às 15h.",
        "orientacoes": ["Evite atravessar ruas alagadas.", "Desligue a energia se a água entrar em casa."],
        "validade_inicio": (relogio.agora - timedelta(minutes=5)).isoformat(),
        "validade_fim": (relogio.agora + timedelta(hours=6)).isoformat(),
        "evidencias": [
            {
                "tipo": "cenario",
                "descricao": "Cenário de 24 h para o Distrito Sanitário V",
                "fonte_id": "open-meteo-previsao",
                "capturada_em": relogio.agora.isoformat(),
            }
        ],
    }
    base.update(extra)
    return base


def test_jornada_rascunho_revisao_publicacao_e_expiracao(equipe):
    ana, rui, cris, publico, relogio = (equipe[k] for k in ("ana", "rui", "cris", "publico", "relogio"))
    r = ana.post(f"{API}/comunicados", json=_comunicado(relogio))
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    assert r.json()["estado"] == "rascunho" and "enviar" in r.json()["acoes"]

    # CA-07: publicar um rascunho é recusado com mensagem clara
    r = cris.post(f"{API}/comunicados/{cid}/publicar")
    assert r.status_code == 409 and "estado" in r.json()["detail"]

    assert ana.post(f"{API}/comunicados/{cid}/enviar").json()["estado"] == "em_revisao"
    # CA-08: o autor não aprova a própria versão (nem tem o papel, nem pela regra)
    assert ana.post(f"{API}/comunicados/{cid}/aprovar").status_code == 403

    # T6.6: a fila de revisão aparece para o revisor, nunca para a analista
    assert [i["id"] for i in rui.get(f"{API}/painel/resumo").json()["aguardando_revisao"]] == [cid]
    painel_ana = ana.get(f"{API}/painel/resumo").json()
    assert painel_ana["aguardando_revisao"] == [] and painel_ana["pode_revisar"] is False

    assert rui.post(f"{API}/comunicados/{cid}/aprovar").json()["estado"] == "aprovado"
    # aprovado mas não publicado não aparece na landing (RN-04)
    assert publico.get(f"{API}/publico/avisos").json() == []

    # T7.4: a prévia é exatamente a versão atual (mesmo hash)
    detalhe = cris.get(f"{API}/comunicados/{cid}").json()
    previa = cris.get(f"{API}/comunicados/{cid}/previa").json()
    assert previa == detalhe["previa"] and previa["titulo"] == "Alerta de alagamento em Afogados"
    assert detalhe["hash_conteudo"] == detalhe["versoes"][-1]["hash_conteudo"]

    r = cris.post(f"{API}/comunicados/{cid}/publicar")
    assert r.status_code == 200 and r.json()["estado"] == "publicado"
    avisos = publico.get(f"{API}/publico/avisos").json()
    assert [a["id"] for a in avisos] == [cid] and avisos[0]["emitido_por"] == "Vigilância em Saúde do Recife"
    estado = publico.get(f"{API}/publico/estado").json()
    assert estado["avisos_ativos"] == 1 and estado["distritos_afetados"] == ["ds-5"]
    assert estado["niveis_por_distrito"] == {"ds-5": "alerta"}
    assert {f["id"] for f in publico.get(f"{API}/publico/fontes").json()} >= {"vacinacao", "ana-telemetria"}
    assert publico.get(f"{API}/publico/avisos", params={"bairro": "afogados"}).json()[0]["id"] == cid
    assert publico.get(f"{API}/publico/avisos", params={"bairro": "boa viagem"}).json() == []

    # T7.5: some da consulta pública no segundo seguinte ao vencimento, mesmo sem a tarefa rodar
    relogio.avancar(hours=6, seconds=1)
    assert publico.get(f"{API}/publico/avisos").json() == []
    assert publico.get(f"{API}/publico/avisos/{cid}").status_code == 404


def test_editar_aprovado_volta_para_revisao_e_gera_diferenca(equipe):
    ana, rui, cris, relogio = (equipe[k] for k in ("ana", "rui", "cris", "relogio"))
    cid = ana.post(f"{API}/comunicados", json=_comunicado(relogio)).json()["id"]
    ana.post(f"{API}/comunicados/{cid}/enviar")
    rui.post(f"{API}/comunicados/{cid}/aprovar")
    r = ana.put(
        f"{API}/comunicados/{cid}",
        json=_comunicado(relogio, texto="Chuva muito forte prevista para a tarde."),
    )
    assert r.json()["estado"] == "em_revisao" and r.json()["versao_atual"] == 2
    assert cris.post(f"{API}/comunicados/{cid}/publicar").status_code == 409
    d = ana.get(f"{API}/comunicados/{cid}/versoes/1/diferenca/2").json()
    assert d["alterados"] == ["texto"]
    assert {"tipo": "inserido", "texto": " muito"} in d["campos"]["texto"]


def test_devolver_exige_justificativa_e_fica_na_linha_do_tempo(equipe):
    ana, rui, relogio = equipe["ana"], equipe["rui"], equipe["relogio"]
    cid = ana.post(f"{API}/comunicados", json=_comunicado(relogio)).json()["id"]
    ana.post(f"{API}/comunicados/{cid}/enviar")
    assert rui.post(f"{API}/comunicados/{cid}/devolver", json={"justificativa": " "}).status_code == 422
    r = rui.post(f"{API}/comunicados/{cid}/devolver", json={"justificativa": "Cite o horário da maré."})
    assert r.json()["estado"] == "devolvido"
    assert [e["tipo"] for e in r.json()["linha_do_tempo"]] == ["versao", "devolver"]


def test_evidencia_sem_fonte_real_e_recusada(equipe):
    ana, relogio = equipe["ana"], equipe["relogio"]
    falsa = _comunicado(relogio)
    falsa["evidencias"][0]["fonte_id"] = "planilha-inventada"
    assert ana.post(f"{API}/comunicados", json=falsa).status_code == 422


def test_ordem_por_nivel_e_depois_data(equipe):
    ana, rui, cris, publico, relogio = (equipe[k] for k in ("ana", "rui", "cris", "publico", "relogio"))
    ids = {}
    for nivel in ("atencao", "critico", "alerta"):
        cid = ana.post(
            f"{API}/comunicados", json=_comunicado(relogio, nivel=nivel, titulo=f"Aviso {nivel}")
        ).json()["id"]
        ana.post(f"{API}/comunicados/{cid}/enviar")
        rui.post(f"{API}/comunicados/{cid}/aprovar")
        cris.post(f"{API}/comunicados/{cid}/publicar")
        ids[nivel] = cid
    assert [a["nivel"] for a in publico.get(f"{API}/publico/avisos").json()] == [
        "critico",
        "alerta",
        "atencao",
    ]
    assert publico.get(f"{API}/publico/estado").json()["nivel_mais_alto"] == "critico"


def test_avaliacao_fluxo_e_rollback_quando_a_auditoria_falha(equipe, sessao, monkeypatch):
    ana, rui = equipe["ana"], equipe["rui"]
    corpo = {
        "territorio_id": "ds-4",
        "periodo_inicio": "2026-10-01",
        "periodo_fim": "2026-10-15",
        "prioridade": "alerta",
        "justificativa": "Previsão de 60 mm em 24 h com maré alta.",
        "evidencias": [],
    }
    r = ana.post(f"{API}/avaliacoes", json=corpo)
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    ana.post(f"{API}/avaliacoes/{aid}/enviar")
    assert "aprovar" not in ana.get(f"{API}/avaliacoes/{aid}").json()["acoes"]  # o autor não vê “Aprovar”

    def quebra(*a, **k):
        raise RuntimeError("falha simulada na auditoria")

    monkeypatch.setattr(fluxo, "auditar", quebra)
    with pytest.raises(RuntimeError):
        rui.post(f"{API}/avaliacoes/{aid}/aprovar")
    monkeypatch.undo()
    # nada mudou: nem o estado, nem a revisão
    estado = sessao.execute(text("select estado from app.avaliacoes where id = :i"), {"i": aid}).scalar()
    revisoes = sessao.execute(text("select count(*) from app.revisoes where alvo = 'avaliacao'")).scalar()
    assert estado == "em_revisao" and revisoes == 0

    assert rui.post(f"{API}/avaliacoes/{aid}/aprovar").json()["estado"] == "aprovado"
    lista = ana.get(f"{API}/avaliacoes").json()
    assert lista["contagens"] == {"aprovado": 1} and lista["itens"][0]["prioridade"] == "alerta"
    acoes = [
        a
        for (a,) in sessao.execute(
            text("select acao from app.auditoria where alvo_id = :i order by id"), {"i": aid}
        )
    ]
    assert acoes == ["avaliacao_criada", "avaliacao_enviada", "avaliacao_aprovada"]
    # aparece nos territórios em atenção do painel
    atencao = ana.get(f"{API}/painel/resumo").json()["territorios_em_atencao"]
    assert atencao[0]["territorio_id"] == "ds-4" and atencao[0]["nivel"] == "alerta"
