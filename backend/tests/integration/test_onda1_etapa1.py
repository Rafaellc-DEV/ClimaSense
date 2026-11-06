"""Onda 1, Etapa 1: frescor em meta.fontes (RF-19), auditoria de leitura (RNF-01), prazo de guarda (RNF-03)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from climasense.etl import frescor
from climasense.servicos import retencao
from tests.conftest import precisa_postgres
from tests.integration.apoio import Relogio, cliente, criar_conta, entrar

pytestmark = [precisa_postgres, pytest.mark.integracao]
API = "/api/v1"


@pytest.fixture
def equipe(sessao):
    relogio = Relogio()
    c = cliente(sessao, relogio)
    criar_conta(sessao, "analista@recife.pe.gov.br", ["analista"])
    assert entrar(c, "analista@recife.pe.gov.br").status_code == 200
    return c, relogio


def _sucesso(sessao, fonte: str, fim: datetime) -> None:
    sessao.execute(
        text("insert into app.etl_execucoes (fonte_id, inicio, fim, status) values (:f, :i, :i, 'sucesso')"),
        {"f": fonte, "i": fim},
    )


def test_meta_fontes_traz_limite_e_desatualizado_sem_confundir_falta_de_dado_com_em_dia(equipe, sessao):
    c, relogio = equipe
    # infodengue: carga recente (em dia); sinan-leptospirose: carga velha (passou do limite); recife-arboviroses: nunca carregada
    _sucesso(sessao, "infodengue", relogio.agora - timedelta(hours=2))
    _sucesso(
        sessao,
        "sinan-leptospirose",
        relogio.agora - timedelta(hours=frescor.limite_frescor_h("sinan-leptospirose") + 5),
    )
    r = c.get(f"{API}/saude/resumo")
    assert r.status_code == 200, r.text
    fontes = {f["id"]: f for f in r.json()["meta"]["fontes"]}
    assert fontes["infodengue"]["desatualizado"] is False
    assert fontes["infodengue"]["limite_frescor_h"] == frescor.limite_frescor_h("infodengue")
    assert fontes["sinan-leptospirose"]["desatualizado"] is True
    sem_carga = fontes["apac-chuva"]
    assert (
        sem_carga["atualizado_em"] is None and sem_carga["desatualizado"] is None
    )  # sem dado: nunca "em dia"
    assert sem_carga["limite_frescor_h"] == frescor.limite_frescor_h("apac-chuva")


def test_rotas_de_indicador_trazem_os_campos_de_frescor(equipe):
    c, _ = equipe
    for rota in (
        "/estagios",
        "/boletim",
        "/saude/bairros",
        "/territorios/prioridades",
    ):
        r = c.get(API + rota)
        assert r.status_code == 200, (rota, r.text)
        for f in r.json()["meta"]["fontes"]:
            assert {"limite_frescor_h", "desatualizado"} <= set(f), rota
    lista = c.get(f"{API}/abrigos").json()
    ids = {f["id"] for f in lista["meta"]["fontes"]}
    assert ids == {"recife-abrigos", "recife-abrigos-ocupacao"}
    ocupacao = next(f for f in lista["meta"]["fontes"] if f["id"] == "recife-abrigos-ocupacao")
    assert ocupacao["atualizado_em"] is None and ocupacao["desatualizado"] is None


def test_fontes_expoe_frescor(equipe):
    c, _ = equipe
    f = {x["id"]: x for x in c.get(f"{API}/fontes").json()}["open-meteo-previsao"]
    assert f["limite_frescor_h"] == frescor.limite_frescor_h("open-meteo-previsao")
    assert f["desatualizado"] is None


def test_leitura_de_saude_e_boletim_e_auditada_sem_corpo(equipe, sessao):
    c, _ = equipe
    assert c.get(f"{API}/saude/bairros", params={"agravo": "dengue", "ano": 2025}).status_code == 200
    assert c.get(f"{API}/saude/resumo").status_code == 200
    assert c.get(f"{API}/boletim").status_code == 200
    assert c.get(f"{API}/estagios").status_code == 200  # fora do escopo desta auditoria
    linhas = (
        sessao.execute(
            text(
                "select acao, alvo_tipo, alvo_id, detalhes, usuario_id is not null as com_usuario from app.auditoria "
                "where acao like 'leitura_%' order by id"
            )
        )
        .mappings()
        .all()
    )
    assert [(x["acao"], x["alvo_id"]) for x in linhas] == [
        ("leitura_dados_saude", f"{API}/saude/bairros"),
        ("leitura_dados_saude", f"{API}/saude/resumo"),
        ("leitura_boletim", f"{API}/boletim"),
    ]
    assert all(x["com_usuario"] and x["alvo_tipo"] == "rota" for x in linhas)
    assert linhas[0]["detalhes"] == {"metodo": "GET", "consulta": {"agravo": "dengue", "ano": "2025"}}
    assert set(linhas[2]["detalhes"]) == {"metodo", "consulta"}  # nunca o corpo da resposta


def test_leitura_sem_login_nao_gera_auditoria(sessao):
    c = cliente(sessao, Relogio())
    assert c.get(f"{API}/saude/resumo").status_code == 401
    assert (
        sessao.execute(text("select count(*) from app.auditoria where acao like 'leitura_%'")).scalar() == 0
    )


def test_limpeza_de_retencao_apaga_so_o_vencido_e_audita_quantidades(sessao):
    agora = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)
    for dias, ok in ((100, False), (91, False), (89, True), (1, True)):
        sessao.execute(
            text("insert into app.tentativas_login (email, em, sucesso) values (:e, :em, :s)"),
            {"e": f"p{dias}@x.co", "em": agora - timedelta(days=dias), "s": ok},
        )
    conta = criar_conta(sessao, "dona@recife.pe.gov.br", ["analista"])
    for i, expirou_ha in enumerate((40, 31, 29, -1)):
        sessao.execute(
            text(
                "insert into app.sessoes (id_hash, usuario_id, csrf_hash, ultimo_uso, expira_em) "
                "values (:h, :u, 'c', :uso, :exp)"
            ),
            {
                "h": f"h{i}",
                "u": conta.id,
                "uso": agora - timedelta(days=50),
                "exp": agora - timedelta(days=expirou_ha),
            },
        )
    primeira = retencao.limpar(sessao, agora)
    assert primeira == {"tentativas_login": 2, "sessoes": 2}
    assert retencao.limpar(sessao, agora) == {"tentativas_login": 0, "sessoes": 0}  # idempotente
    assert sessao.execute(text("select count(*) from app.tentativas_login")).scalar() == 2
    assert sessao.execute(text("select count(*) from app.sessoes")).scalar() == 2
    detalhes = sessao.execute(
        text("select detalhes from app.auditoria where acao = 'limpeza_retencao' order by id limit 1")
    ).scalar()
    assert detalhes["tentativas_login"] == 2 and detalhes["sessoes"] == 2
    assert "email" not in str(detalhes)


def test_sincronizar_frescor_alinha_o_banco_ao_toml(sessao):
    sessao.execute(text("update app.fontes set limite_desatualizacao_h = 7 where id = 'apac-chuva'"))
    r = retencao.sincronizar_frescor(sessao)
    assert r["fontes_alteradas"] >= 1
    banco = sessao.execute(
        text("select id, limite_desatualizacao_h from app.fontes where id in ('apac-chuva','infodengue')")
    ).all()
    esperado = {f: max(1, -int(-frescor.limite_frescor_h(f) // 1)) for f in ("apac-chuva", "infodengue")}
    assert dict(banco) == esperado
    assert retencao.sincronizar_frescor(sessao) == {"fontes_alteradas": 0}
