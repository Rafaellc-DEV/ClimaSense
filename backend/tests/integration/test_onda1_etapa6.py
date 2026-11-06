"""Onda 1, Etapa 6: vulnerabilidade (RF-02, RF-03, RF-04, RF-07, RF-25, RNF-03, RN-01, RN-13)."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import text

from climasense.territorio import carga
from tests.conftest import precisa_postgres
from tests.integration.apoio import Relogio, cliente, criar_conta, entrar

pytestmark = [precisa_postgres, pytest.mark.integracao]
T = "/api/v1/territorios"
PREMISSAS = {
    "chuva_prevista_mm": 72,
    "duracao_h": 24,
    "chuva_acumulada_mm": 40,
    "mare_m": 2.3,
    "horizonte_h": 24,
}
# quadrado de ~1 km em volta de (lon, lat) = (-34.9, -8.05)
QUADRADO = {
    "type": "Polygon",
    "coordinates": [[[-34.91, -8.06], [-34.89, -8.06], [-34.89, -8.04], [-34.91, -8.04], [-34.91, -8.06]]],
}


@pytest.fixture
def c(sessao):
    carga.sincronizar_territorios(sessao, carga.geo_local())
    http = cliente(sessao, Relogio())
    criar_conta(sessao, "ana@recife.pe.gov.br", ["analista"])
    assert entrar(http, "ana@recife.pe.gov.br").status_code == 200
    return http


def _bairros(sessao, n=3) -> list[tuple[str, str]]:
    return [
        (i, p)
        for i, p in sessao.execute(
            text("select id, pai_id from app.territorios where tipo = 'bairro' order by id limit :n"),
            {"n": n},
        )
    ]


def _execucao(sessao, fonte: str):
    return sessao.execute(
        text(
            "insert into app.etl_execucoes (fonte_id, status, fim) values (:f, 'sucesso', now()) returning id"
        ),
        {"f": fonte},
    ).scalar_one()


def _populacao(sessao, bairro: str, faixas: dict[str, int | None]) -> None:
    ex = _execucao(sessao, "ibge-censo-2022-bairro")
    for faixa, pessoas in faixas.items():
        sessao.execute(
            text(
                "insert into silver.populacao_bairro (bairro_id, ano, faixa, pessoas, suprimido, fonte_id, execucao_id) "
                "values (:b, 2022, :f, :p, :s, 'ibge-censo-2022-bairro', :e)"
            ),
            {"b": bairro, "f": faixa, "p": pessoas, "s": pessoas is None, "e": ex},
        )


def _equipamento(sessao, cnes, bairro, distrito, lon, lat) -> None:
    ex = _execucao(sessao, "cnes-equipamentos")
    sessao.execute(
        text(
            "insert into silver.equipamentos_saude (cnes, nome, tipo, esfera, bairro_id, distrito_id, latitude, longitude, "
            "fonte_id, execucao_id) values (:c, :n, 'UBS', 'Municipal', :b, :d, :la, :lo, 'cnes-equipamentos', :e)"
        ),
        {"c": cnes, "n": f"Unidade {cnes}", "b": bairro, "d": distrito, "la": lat, "lo": lon, "e": ex},
    )


def _area(sessao, aid, bairro, regional, geometria=QUADRADO) -> None:
    ex = _execucao(sessao, "recife-areas-risco")
    sessao.execute(
        text(
            "insert into silver.areas_risco (id, tipo, grau, regional, bairro_id, geometria, fonte_id, execucao_id) "
            "values (:i, 'deslizamento', 'alto', :r, :b, cast(:g as jsonb), 'recife-areas-risco', :e)"
        ),
        {"i": aid, "r": regional, "b": bairro, "g": json.dumps(geometria), "e": ex},
    )


# ------------------------------------------------------------------ tabelas vazias (RN-01)
def test_tabelas_vazias_dizem_qual_fonte_falta_e_nunca_zero(c, sessao):
    b, _ = _bairros(sessao, 1)[0]
    eq = c.get(f"{T}/camadas/equipamentos-saude").json()
    assert eq["meta"]["dados_insuficientes"] is True and eq["dados"]["features"] == []
    assert "Dados insuficientes: falta a fonte cnes-equipamentos" in eq["meta"]["avisos"]
    assert eq["meta"]["fontes"][0]["id"] == "cnes-equipamentos"
    vul = c.get(f"{T}/camadas/vulneraveis").json()
    assert vul["meta"]["dados_insuficientes"] is True and vul["dados"]["itens"] == []
    assert "Dados insuficientes: falta a fonte ibge-censo-2022-bairro" in vul["meta"]["avisos"]
    assert vul["meta"]["deficiencia"].startswith("Dados insuficientes: não há dado público de deficiência")
    ar = c.get(f"{T}/camadas/areas-risco").json()
    assert ar["meta"]["dados_insuficientes"] is True and ar["meta"]["cobertura"] is None
    assert "Dados insuficientes: falta a fonte recife-areas-risco" in ar["meta"]["avisos"]
    r = c.get(f"{T}/{b}/resumo-vulnerabilidade").json()
    assert r["meta"]["dados_insuficientes"] is True
    d = r["dados"]
    assert d["idosos_60_mais"] is None and d["criancas_0_14"] is None
    assert d["equipamentos"] == [] and d["equipamentos_em_area_de_risco"] is None and d["areas_risco"] is None
    assert d["cobertura_risco_parcial"] is True and d["abrigos"] == 0
    assert len(r["meta"]["avisos"]) == 3


# ------------------------------------------------------------------ vulneráveis, supressão (RNF-03)
def test_vulneraveis_aplicam_supressao_do_projeto_e_do_ibge(c, sessao):
    (b1, ds1), (b2, _), (b3, _) = _bairros(sessao)
    _populacao(sessao, b1, {"0-4": 3, "0-14": 900, "total": 9000, "60+": 1500, "70+": 0})
    _populacao(sessao, b2, {"0-4": None, "60+": 40})
    r = c.get(f"{T}/camadas/vulneraveis").json()
    assert r["meta"]["ano"] == 2022 and r["meta"]["supressao_minima"] == 5
    assert r["meta"]["dados_insuficientes"] is False
    itens = {i["bairro_id"]: i for i in r["dados"]["itens"]}
    assert len(itens) == 94
    i1 = itens[b1]
    assert i1["criancas_0_4"] is None and i1["suprimido"]["criancas_0_4"] is True  # 3 < 5
    assert i1["criancas_0_14"] == 900 and i1["idosos_60_mais"] == 1500 and i1["total"] == 9000
    assert i1["idosos_70_mais"] == 0 and i1["suprimido"]["idosos_70_mais"] is False  # zero medido
    assert i1["deficiencia"] is None and i1["distrito_id"] == ds1
    i2 = itens[b2]
    assert i2["criancas_0_4"] is None and i2["suprimido"]["criancas_0_4"] is True  # oculto pelo IBGE
    assert i2["idosos_60_mais"] == 40
    i3 = itens[b3]  # sem linha: sem dado, não suprimido
    assert i3["idosos_60_mais"] is None and not any(i3["suprimido"].values())
    assert "total" in i1 and "nome" in i1
    assert not any("cpf" in k or "nome_pessoa" in k for k in i1)


def test_supressao_minima_vem_da_configuracao(sessao):
    carga.sincronizar_territorios(sessao, carga.geo_local())
    http = cliente(sessao, Relogio(), supressao_minima=50)
    criar_conta(sessao, "bia@recife.pe.gov.br", ["analista"])
    entrar(http, "bia@recife.pe.gov.br")
    b, _ = _bairros(sessao, 1)[0]
    _populacao(sessao, b, {"60+": 40, "0-14": 60})
    i = next(i for i in http.get(f"{T}/camadas/vulneraveis").json()["dados"]["itens"] if i["bairro_id"] == b)
    assert i["idosos_60_mais"] is None and i["suprimido"]["idosos_60_mais"] is True
    assert i["criancas_0_14"] == 60


# ------------------------------------------------------------------ equipamentos e áreas de risco
def test_equipamentos_viram_pontos_sem_nada_de_pessoa(c, sessao):
    (b1, ds1), _, _ = _bairros(sessao)
    _equipamento(sessao, "1234567", b1, ds1, -34.9, -8.05)
    d = c.get(f"{T}/camadas/equipamentos-saude").json()
    assert d["meta"]["dados_insuficientes"] is False
    f = d["dados"]["features"][0]
    assert f["geometry"] == {"type": "Point", "coordinates": [-34.9, -8.05]}
    assert set(f["properties"]) == {"cnes", "nome", "tipo", "esfera", "bairro_id", "distrito_id"}


def test_areas_de_risco_com_cobertura_parcial(c, sessao):
    (b1, _), (b2, _), _ = _bairros(sessao)
    _area(sessao, "a1", b1, "Regional 1")
    _area(sessao, "a2", b2, "Regional 3")
    _area(sessao, "a3", b2, "Regional 3")
    d = c.get(f"{T}/camadas/areas-risco").json()
    assert len(d["dados"]["features"]) == 3
    assert set(d["dados"]["features"][0]["properties"]) == {"id", "tipo", "grau", "regional", "bairro_id"}
    cob = d["meta"]["cobertura"]
    assert cob["regionais_com_dado"] == ["Regional 1", "Regional 3"]
    assert cob["bairros_com_dado"] == 2 and cob["total_bairros"] == 94 and cob["parcial"] is True
    assert "não significa bairro sem risco" in cob["texto"]


# ------------------------------------------------------------------ cruzamento (RF-04, RF-07)
def test_resumo_cruza_equipamentos_com_areas_de_risco(c, sessao):
    (b1, ds1), (b2, _), _ = _bairros(sessao)
    _populacao(sessao, b1, {"60+": 1500, "0-14": 2100})
    _equipamento(sessao, "0000001", b1, ds1, -34.90, -8.05)  # dentro do quadrado
    _equipamento(sessao, "0000002", b1, ds1, -34.50, -8.05)  # fora
    _equipamento(sessao, "0000003", b1, ds1, None, None)  # sem coordenada: conta como equipamento, não cruza
    _area(sessao, "a1", b1, "Regional 1")
    sessao.execute(
        text(
            "insert into app.abrigos (nome, bairro_id, endereco, latitude, longitude, origem, codigo_fonte, aberto) "
            "values ('Escola X', :b, 'Rua Y', -8.05, -34.9, 'dados-abertos', 'x1', true)"
        ),
        {"b": b1},
    )
    d = c.get(f"{T}/{b1}/resumo-vulnerabilidade").json()
    assert d["meta"]["dados_insuficientes"] is False and d["meta"]["avisos"] == []
    r = d["dados"]
    assert r["idosos_60_mais"] == 1500 and r["criancas_0_14"] == 2100
    assert {e["cnes"] for e in r["equipamentos"]} == {"0000001", "0000002", "0000003"}
    assert r["equipamentos_em_area_de_risco"] == 1
    assert r["areas_risco"] == 1 and r["cobertura_risco_parcial"] is True and r["abrigos"] == 1
    # o distrito soma: falta população de outros bairros dele, então o número fica nulo (nunca subestimado)
    dd = c.get(f"{T}/{ds1}/resumo-vulnerabilidade").json()["dados"]
    assert len(dd["equipamentos"]) == 3 and dd["idosos_60_mais"] is None and dd["abrigos"] == 1
    # outro bairro: não herda o equipamento de b1
    r2 = c.get(f"{T}/{b2}/resumo-vulnerabilidade").json()["dados"]
    assert r2["equipamentos"] == [] and r2["areas_risco"] == 0 and r2["equipamentos_em_area_de_risco"] == 0


def test_resumo_valida_o_territorio(c):
    assert c.get(f"{T}/xyz/resumo-vulnerabilidade").status_code == 422
    assert c.get(f"{T}/bairro-inexistente-zz/resumo-vulnerabilidade").status_code == 404
    assert c.get(f"{T}/recife/resumo-vulnerabilidade").status_code == 200


def test_camadas_exigem_login(sessao):
    anonimo = cliente(sessao, Relogio())
    for rota in ("camadas/equipamentos-saude", "camadas/vulneraveis", "camadas/areas-risco"):
        assert anonimo.get(f"{T}/{rota}").status_code == 401
    assert anonimo.get(f"{T}/ds-1/resumo-vulnerabilidade").status_code == 401


# ------------------------------------------------------------------ prioridade (RF-06, RF-22) e simulador (RF-25)
def _carga_ocorrencias(sessao, linhas: list[tuple[str, str, int]]) -> None:
    ex = _execucao(sessao, "recife-alagamento")
    for territorio, tipo, quantas in linhas:
        for _ in range(quantas):
            sessao.execute(
                text(
                    "insert into silver.ocorrencias (fonte_id, territorio_id, registrado_em, tipo, execucao_id) "
                    "values ('recife-alagamento', :t, '2020-05-01T10:00:00Z', :tipo, :e)"
                ),
                {"t": territorio, "tipo": tipo, "e": ex},
            )


def test_prioridade_mostra_idosos_e_criancas_sem_mudar_a_ordem(c, sessao):
    (b1, _), (b2, _), _ = _bairros(sessao)
    _carga_ocorrencias(sessao, [(b1, "alagamento", 2), (b2, "alagamento", 9)])
    antes = c.get(f"{T}/prioridade", params={"nivel": "bairro"}).json()["dados"]["itens"]
    assert all(i["idosos_60_mais"] is None and i["criancas_0_14"] is None for i in antes)
    _populacao(sessao, b1, {"60+": 99999, "0-14": 88888})  # b1 tem mais gente, mas menos ocorrências
    depois = c.get(f"{T}/prioridade", params={"nivel": "bairro"}).json()["dados"]["itens"]
    assert [i["territorio_id"] for i in depois] == [i["territorio_id"] for i in antes]
    assert depois[0]["territorio_id"] == b2 and depois[0]["posicao"] == 1
    item1 = next(i for i in depois if i["territorio_id"] == b1)
    assert item1["idosos_60_mais"] == 99999 and item1["criancas_0_14"] == 88888
    assert "idosos e crianças" in " ".join(c.get(f"{T}/prioridade").json()["meta"]["avisos"])


def test_simulador_traz_impacto_em_pessoas_e_soma_bairros_em_alerta(c, sessao):
    (b1, ds1), (b2, _), (b3, _) = _bairros(sessao)
    _carga_ocorrencias(sessao, [(b1, "alagamento", 14), (b1, "deslizamento", 2), (b2, "alagamento", 0)])
    _populacao(sessao, b1, {"60+": 1200, "0-14": 800})
    _populacao(sessao, b2, {"60+": 300, "0-14": 3})  # 3 crianças: suprimido, não entra na soma
    _equipamento(sessao, "0000001", b1, ds1, -34.9, -8.05)
    corpo = c.post("/api/v1/cenarios/simular", json=PREMISSAS).json()["dados"]
    por_id = {i["territorio_id"]: i for i in corpo["itens"]}
    imp = por_id[b1]["impacto_pessoas"]
    assert imp["idosos_60_mais"] == 1200 and imp["criancas_0_14"] == 800
    assert imp["equipamentos_saude"] == 1 and imp["deficiencia"] is None and imp["total_pessoas"] == 2000
    assert por_id[b2]["impacto_pessoas"]["criancas_0_14"] is None
    assert por_id[b3]["impacto_pessoas"]["idosos_60_mais"] is None  # sem linha de população: sem dado
    assert corpo["resumo"]["impacto_pessoas_aviso"] is None
    resumo = corpo["resumo"]["pessoas_vulneraveis_em_alerta"]
    assert resumo["bairros_em_alerta"] >= 2 and resumo["parcial"] is True  # há bairros em alerta sem número
    assert resumo["idosos_60_mais"] == 1500 and resumo["criancas_0_14"] == 800
    assert "%" not in json.dumps(resumo) and "probabilidade" in resumo["criterio"]


def test_simulador_sem_fonte_de_populacao_segue_nulo_com_aviso(c):
    corpo = c.post("/api/v1/cenarios/simular", json=PREMISSAS).json()["dados"]
    assert all(i["impacto_pessoas"] is None for i in corpo["itens"])
    assert corpo["resumo"]["impacto_pessoas_aviso"].startswith("Dados insuficientes")
    assert corpo["resumo"]["pessoas_vulneraveis_em_alerta"] is None


def test_faixa_80_mais_rejeitada_e_70_mais_aceita(c, sessao):
    """Migração 0018 (ADR 0010): o IBGE não publica 80+ por bairro; nada é estimado."""
    from sqlalchemy.exc import IntegrityError

    (b1, _), _, _ = _bairros(sessao)
    _populacao(sessao, b1, {"70+": 10})
    with pytest.raises(IntegrityError):
        _populacao(sessao, b1, {"80+": 1})
    sessao.rollback()
