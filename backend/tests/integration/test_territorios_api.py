import mongomock
import pytest

from climasense.api import deps
from climasense.territorio import carga
from tests.conftest import precisa_postgres
from tests.integration.apoio import Relogio, cliente, criar_conta, entrar

pytestmark = [precisa_postgres, pytest.mark.integracao]


@pytest.fixture
def c(sessao):
    geo = carga.geo_local()
    atlas = mongomock.MongoClient()
    carga.salvar_atlas(atlas, geo, "Recife")
    carga.salvar_hidrografia(atlas, carga.preparar_hidrografia(carga.carregar_hidrografia()), "Recife")
    assert carga.sincronizar_territorios(sessao, geo) == 103
    http = cliente(sessao, Relogio())
    http.app.dependency_overrides[deps.mongo] = lambda: atlas
    criar_conta(sessao, "ana@recife.pe.gov.br", ["analista"])
    entrar(http, "ana@recife.pe.gov.br")
    return http


def test_arvore_de_territorios(c):
    t = c.get("/api/v1/territorios").json()
    assert len(t) == 103
    ds4 = next(x for x in t if x["id"] == "ds-4")
    assert ds4["nome_exibicao"] == "Distrito Sanitário IV" and ds4["pai_id"] == "recife"


def test_geojson_com_etag(c):
    r = c.get("/api/v1/territorios/distritos.geojson")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/geo+json")
    assert len(r.json()["features"]) == 8
    assert (
        c.get(
            "/api/v1/territorios/distritos.geojson", headers={"If-None-Match": r.headers["etag"]}
        ).status_code
        == 304
    )
    assert len(c.get("/api/v1/territorios/hidrografia.geojson").json()["features"]) == 81


def test_indicadores_reais_e_dados_insuficientes(c):
    r = c.get("/api/v1/territorios/indicadores", params={"indicador": "quantidade_bairros"}).json()
    assert [d["valor"] for d in r["dados"]] == [11, 18, 16, 12, 16, 5, 13, 3]
    assert r["meta"]["dados_insuficientes"] is False
    vac = c.get("/api/v1/territorios/indicadores", params={"indicador": "vacinacao"}).json()
    assert vac["meta"]["dados_insuficientes"] is True and all(d["valor"] is None for d in vac["dados"])
    oc = c.get("/api/v1/territorios/indicadores", params={"indicador": "ocorrencias"}).json()
    assert oc["meta"]["dados_insuficientes"] is True and all(d["valor"] is None for d in oc["dados"])
    assert c.get("/api/v1/territorios/indicadores", params={"indicador": "risco"}).status_code == 400


def test_mapa_portatil(c):
    r = c.get("/api/v1/territorios/mapa-portatil")
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    assert '"waterCount": 81' in r.text


def test_rotas_publicas_sem_login(sessao, c):
    publico = cliente(sessao, Relogio())
    assert publico.get("/api/v1/publico/estado").json() == {
        "avisos_ativos": 0,
        "distritos_afetados": [],
        "niveis_por_distrito": {},
        "nivel_mais_alto": None,
        "principal": None,
        "atualizado_em": "2026-10-15T20:00:00Z",
    }
    nomes = [
        b["nome"] for b in publico.get("/api/v1/publico/territorios/busca", params={"q": "brasilia"}).json()
    ]
    assert nomes == ["Brasilia Teimosa"]
    assert publico.get("/api/v1/territorios").status_code == 401
