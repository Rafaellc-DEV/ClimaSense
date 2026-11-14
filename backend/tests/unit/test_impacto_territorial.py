"""Fluxo territorial isolado: sem rede, configurações pessoais ou banco remoto."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from climasense.dominio.estagio import Parametros
from climasense.dominio.simulador import Historico
from climasense.ml.alagamento import prever
from climasense.servicos import impacto_territorial as impacto

AGORA = datetime(2026, 5, 10, 12, tzinfo=UTC)


def horaria(valor, n=72):
    return [(AGORA + timedelta(hours=h), valor) for h in range(n)]


@pytest.fixture
def fontes(monkeypatch):
    est = {
        "distritos": {"ds-1": "Distrito 1", "ds-2": "Distrito 2"},
        "bairros": [("bairro-a", "A", "ds-1"), ("bairro-b", "B", "ds-2")],
        "historico": {"bairro-a": Historico(5, 5, 2014), "bairro-b": Historico(0, 0, 2014)},
    }
    monkeypatch.setattr(impacto.simulador, "_estatico", lambda db: est)
    monkeypatch.setattr(impacto.estagios, "parametros_atuais", lambda db: {"parametros": Parametros()})
    monkeypatch.setattr(
        impacto.cenarios,
        "previsao_por_emissao_distritos",
        lambda *a: {"ds-1": {AGORA: horaria(8)}, "ds-2": {AGORA: horaria(0)}},
    )
    monkeypatch.setattr(impacto.cenarios, "mare_prevista", lambda *a: (AGORA, horaria(1.0)))
    monkeypatch.setattr(
        impacto, "observada_72h", lambda *a: {"ds-1": {"mm": 150, "lida_em": AGORA, "estacoes": 2}}
    )
    monkeypatch.setattr(impacto, "suscetibilidade", lambda db: {"bairro-a": {"alta": 0.5, "coberta": 0.9}})
    monkeypatch.setattr(impacto.simulador, "vulneraveis_por_territorio", lambda db: None)
    arbo = {d: {"classe_impacto": None, "agravos_em_destaque": [], "agravos": []} for d in est["distritos"]}
    monkeypatch.setattr(
        impacto.arboviroses_cenario, "montar", lambda *a: {"por_distrito": arbo, "resumo": None}
    )
    monkeypatch.setattr(
        impacto.ml,
        "payload",
        lambda *a: {"disponivel": False, "motivo": "Reprovado", "modelo": None, "itens": []},
    )
    return est


def test_previsao_preserva_distritos_mare_suscetibilidade_e_fallback(fontes):
    r = impacto.analisar(None, AGORA)
    a, b = r["itens"][:2]
    assert a["avaliacao"]["chuva_no_horizonte_mm"] == 192
    assert b["avaliacao"]["chuva_no_horizonte_mm"] == 0
    assert a["classe_alagamento"] == "critico"
    assert a["avaliacao"]["suscetibilidade"]["alta"] == 0.5
    assert "não previsão" in a["avaliacao"]["contexto_deslizamento"]
    assert "atenção" in a["avaliacao"]["contexto_deslizamento"]
    assert a["ml_alagamento"] is None and not r["ml_alagamento"]["disponivel"]
    assert b["classe_deslizamento"] == "sem_dados"
    assert r["contexto"] == "previsao_atual"


@pytest.mark.parametrize("horas", [6, 12, 24, 72])
def test_horizonte_usa_horas_reais_sem_distribuir_uniformemente(fontes, monkeypatch, horas):
    serie = [(t, 0 if i < 24 else 10) for i, (t, _) in enumerate(horaria(0))]
    monkeypatch.setattr(
        impacto.cenarios, "previsao_por_emissao_distritos", lambda *a: {"ds-1": {AGORA: serie}}
    )
    r = impacto.analisar(None, AGORA, horas)
    a = r["itens"][0]
    assert a["avaliacao"]["chuva_no_horizonte_mm"] == max(0, horas - 24) * 10
    assert a["avaliacao"]["fim_validade"] == AGORA + timedelta(hours=horas)


@pytest.mark.parametrize("emissao", [None, AGORA - timedelta(hours=7), AGORA + timedelta(hours=1)])
def test_previsao_ausente_vencida_ou_futura_nao_vira_zero(fontes, monkeypatch, emissao):
    monkeypatch.setattr(
        impacto.cenarios,
        "previsao_por_emissao_distritos",
        lambda *a: {"ds-1": {emissao: horaria(8)}} if emissao else {},
    )
    r = impacto.analisar(None, AGORA)
    assert r["itens"][0]["estagio_sugerido"] == "sem_dados"
    assert r["itens"][0]["avaliacao"]["chuva_no_horizonte_mm"] is None


def test_serie_incompleta_duplicada_e_horizonte_fora_da_cobertura(fontes, monkeypatch):
    assert impacto.acumulado_completo(horaria(1, 23), AGORA, 24) is None
    assert impacto.acumulado_completo(horaria(1, 23) + horaria(1, 1), AGORA, 24) is None
    monkeypatch.setattr(
        impacto.cenarios, "previsao_por_emissao_distritos", lambda *a: {"ds-1": {AGORA: horaria(8, 12)}}
    )
    assert impacto.analisar(None, AGORA, 72)["itens"][0]["estagio_sugerido"] == "sem_dados"


def test_numeros_nao_finitos_viram_ausentes_sem_quebrar_json(fontes, monkeypatch):
    import json

    monkeypatch.setattr(
        impacto.cenarios,
        "previsao_por_emissao_distritos",
        lambda *a: {"ds-1": {AGORA: horaria(float("nan"))}},
    )
    monkeypatch.setattr(impacto.cenarios, "mare_prevista", lambda *a: (AGORA, horaria(float("inf"))))
    r = impacto.analisar(None, AGORA)
    assert r["itens"][0]["estagio_sugerido"] == "sem_dados"
    json.dumps(r, allow_nan=False, default=str)


def test_hash_canonico_independe_do_fuso(fontes):
    from datetime import timezone

    r = impacto.analisar(None, AGORA)
    outro = deepcopy(r)
    fuso = timezone(-timedelta(hours=3))
    for item in outro["itens"]:
        a = item["avaliacao"]
        for chave in (
            "emitido_em_fonte",
            "mare_emitida_em",
            "inicio_validade",
            "fim_validade",
            "observada_em",
        ):
            if a.get(chave) is not None:
                a[chave] = a[chave].astimezone(fuso)
        for chave in ("serie_chuva", "serie_mare"):
            a[chave] = [(t.astimezone(fuso), v) for t, v in a[chave]]
    assert [d["hash_entrada"] for d in prever.registros(r)] == [
        d["hash_entrada"] for d in prever.registros(outro)
    ]


def test_mare_vencida_e_falha_do_ml_preservam_resposta(fontes, monkeypatch):
    monkeypatch.setattr(impacto.cenarios, "mare_prevista", lambda *a: (AGORA - timedelta(days=2), horaria(1)))

    def falhar(*a):
        raise RuntimeError("Indisponível")

    monkeypatch.setattr(impacto.ml, "payload", falhar)
    r = impacto.analisar(None, AGORA)
    assert not r["ml_alagamento"]["disponivel"]
    assert r["itens"][0]["estagio_sugerido"] == "sem_dados"


def test_persistencia_idempotente_e_sem_ml_reprovado(fontes):
    r = impacto.analisar(None, AGORA)
    dados = prever.registros(r)
    assert len(dados) == 4 and all(d["status_validacao"] == "regra_experimental" for d in dados)
    outro = deepcopy(r)
    outro["calculado_em"] += timedelta(minutes=1)
    assert [d["hash_entrada"] for d in prever.registros(outro)] == [d["hash_entrada"] for d in dados]

    class DB:
        hashes = set()
        commits = 0

        def execute(self, sql, p):
            assert "on conflict (hash_entrada) do nothing" in str(sql)
            novo = p["hash_entrada"] not in self.hashes
            self.hashes.add(p["hash_entrada"])
            return SimpleNamespace(rowcount=int(novo))

        def commit(self):
            self.commits += 1

        def rollback(self):
            pytest.fail("Rollback inesperado")

    db = DB()
    assert prever.persistir(db, r) == 4
    assert prever.persistir(db, outro) == 0 and db.commits == 2
    with pytest.raises(ValueError, match="previsão atual"):
        prever.registros({"contexto": "cenario_hipotetico"})


def test_rota_preserva_envelope_metadados_e_nao_grava(fontes, monkeypatch):
    from fastapi.testclient import TestClient

    from climasense.api.autorizacao import relogio
    from climasense.api.envelope import FonteMeta
    from climasense.api.main import criar_app
    from climasense.api.routers import cenarios
    from climasense.infra.postgres import obter_sessao
    from tests.conftest import configuracao_teste

    app = criar_app(configuracao_teste())
    app.dependency_overrides[cenarios.consultar] = lambda: None
    app.dependency_overrides[obter_sessao] = lambda: None
    app.dependency_overrides[relogio] = lambda: AGORA
    monkeypatch.setattr(
        cenarios.servico_fontes,
        "meta",
        lambda db, f, a: FonteMeta(id=f, nome=f, tipo="derivada", status="planejada"),
    )
    rota = next(r for r in cenarios.router.routes if r.path == "/cenarios/impacto-previsto")
    assert any(hasattr(d.call, "permissao") for d in rota.dependant.dependencies)
    c = TestClient(app)
    r = c.get("/api/v1/cenarios/impacto-previsto?horizonte_h=24")
    assert r.status_code == 200
    assert r.json()["dados"]["contexto"] == "previsao_atual"
    assert r.json()["meta"]["fontes"][0]["id"] == "open-meteo-previsao"
    assert not r.json()["dados"]["ml_alagamento"]["disponivel"]
    assert c.get("/api/v1/cenarios/impacto-previsto?horizonte_h=73").status_code == 422
