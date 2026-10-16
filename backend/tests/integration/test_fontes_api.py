import pytest
from sqlalchemy import text

from climasense.api.routers import fontes
from tests.conftest import precisa_postgres
from tests.integration.apoio import Relogio, cliente, criar_conta, entrar

pytestmark = [precisa_postgres, pytest.mark.integracao]


def test_status_das_fontes_e_disparo_pelo_administrador(sessao):
    chamadas = []
    c = cliente(sessao, Relogio())
    c.app.dependency_overrides[fontes.executor_em_segundo_plano] = lambda: lambda *a: chamadas.append(a)
    criar_conta(sessao, "admin@recife.pe.gov.br", ["administrador"])
    entrar(c, "admin@recife.pe.gov.br")
    status = {f["id"]: f["status"] for f in c.get("/api/v1/fontes").json()}
    assert status["ana-telemetria"] == "planejada" and status["recife-alagamento"] == "planejada"
    assert status["vacinacao"] == "desatualizada"  # implementada, mas ainda sem nenhuma carga
    r = c.post("/api/v1/etl/execucoes", json={"fonte_id": "open-meteo-previsao"})
    assert r.status_code == 202 and r.json()["status"] == "em_andamento"
    execucao_id = r.json()["id"]
    assert chamadas and chamadas[0][0] == "open-meteo-previsao"
    sessao.execute(
        text("update app.etl_execucoes set status='falha', fim=now() + interval '1 hour' where id = :i"),
        {"i": execucao_id},
    )
    assert c.get("/api/v1/fontes/open-meteo-previsao").json()["status"] == "com_falha"
    assert execucao_id in [e["id"] for e in c.get("/api/v1/fontes/open-meteo-previsao/execucoes").json()]
    assert c.post("/api/v1/etl/execucoes", json={"fonte_id": "inexistente"}).status_code == 404
