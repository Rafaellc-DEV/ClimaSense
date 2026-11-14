"""Migração e consulta reais, exclusivamente no Postgres descartável DATABASE_URL_TESTE."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from climasense.ml.alagamento.prever import persistir
from climasense.servicos.impacto_territorial import analisar
from climasense.territorio import carga
from tests.conftest import precisa_postgres

pytestmark = [precisa_postgres, pytest.mark.integracao]
AGORA = datetime(2026, 5, 10, 12, tzinfo=UTC)


def test_previsao_por_distrito_e_persistencia_real_idempotente(sessao, monkeypatch):
    from climasense.ml.alagamento import armazenamento

    monkeypatch.setattr(armazenamento, "carregar_em_cache", lambda: None)
    carga.sincronizar_territorios(sessao, carga.geo_local())
    ids = {}
    for fonte in ("open-meteo-previsao", "open-meteo-mare", "apac-chuva"):
        ids[fonte] = sessao.execute(
            text(
                "insert into app.etl_execucoes (fonte_id, status, fim) values (:f, 'sucesso', :a) returning id"
            ),
            {"f": fonte, "a": AGORA},
        ).scalar_one()
    for ds, valor in (("ds-1", 8), ("ds-2", 0), ("recife", 1)):
        fonte = "open-meteo-mare" if ds == "recife" else "open-meteo-previsao"
        for h in range(72):
            sessao.execute(
                text(
                    "insert into silver.observacoes (fonte_id, territorio_id, variavel, valor, unidade, tipo, "
                    "observado_em, emitido_em, coletado_em, execucao_id) "
                    "values (:f, :ds, :v, :mm, :u, 'prevista', :h, :a, :a, :ex)"
                ),
                {
                    "f": fonte,
                    "ds": ds,
                    "v": "mare_m" if ds == "recife" else "chuva_mm",
                    "mm": valor,
                    "u": "m" if ds == "recife" else "mm",
                    "h": AGORA + timedelta(hours=h),
                    "a": AGORA,
                    "ex": ids[fonte],
                },
            )
    # Emissão futura não pode contaminar o snapshot solicitado em AGORA.
    sessao.execute(
        text(
            "insert into silver.observacoes (fonte_id, territorio_id, variavel, valor, unidade, tipo, "
            "observado_em, emitido_em, coletado_em, execucao_id) values ('open-meteo-previsao', 'ds-1', "
            "'chuva_mm', 999, 'mm', 'prevista', :a, :futuro, :futuro, :ex)"
        ),
        {"a": AGORA, "futuro": AGORA + timedelta(hours=1), "ex": ids["open-meteo-previsao"]},
    )
    sessao.execute(
        text(
            "insert into silver.estacoes (id, fonte_id, codigo_fonte, nome, lat, lon, territorio_id) "
            "values ('teste-ds1', 'apac-chuva', 'teste-ds1', 'Estação de teste', -8, -34.9, 'ds-1')"
        )
    )
    for instante, valor in ((AGORA - timedelta(minutes=1), 150), (AGORA + timedelta(hours=1), 999)):
        sessao.execute(
            text(
                "insert into silver.apac_chuva_leituras (estacao_id, lida_em, janela_h, valor_mm, coletado_em, visto_em, execucao_id) "
                "values ('teste-ds1', :t, 72, :v, :t, :t, :ex)"
            ),
            {"t": instante, "v": valor, "ex": ids["apac-chuva"]},
        )
    sessao.flush()
    r = analisar(sessao, AGORA, 24)
    ds = {i["territorio_id"]: i for i in r["itens"] if i["nivel"] == "distrito"}
    assert ds["ds-1"]["avaliacao"]["chuva_no_horizonte_mm"] == 192
    assert ds["ds-2"]["avaliacao"]["chuva_no_horizonte_mm"] == 0
    assert ds["ds-3"]["avaliacao"]["chuva_no_horizonte_mm"] is None
    assert ds["ds-1"]["avaliacao"]["chuva_observada_72h_mm"] == 150
    assert ds["ds-2"]["avaliacao"]["chuva_observada_72h_mm"] is None
    assert not r["ml_alagamento"]["disponivel"]
    assert persistir(sessao, r) == 188
    assert persistir(sessao, r) == 0
    linhas = sessao.execute(text("select count(*) from gold.previsoes_impacto")).scalar_one()
    assert linhas == 188
    for comando in (
        "update silver.inferencias_impacto set metodo = 'alterado'",
        "delete from silver.inferencias_impacto",
    ):
        with pytest.raises(DBAPIError), sessao.begin_nested():
            sessao.execute(text(comando))


def test_0025_view_e_permissoes_minimas(engine_teste):
    with engine_teste.connect() as c:
        assert c.execute(text("select to_regclass('gold.previsoes_impacto')")).scalar_one()
        for p in ("SELECT", "INSERT"):
            assert c.execute(
                text("select has_table_privilege('climasense_app', 'silver.inferencias_impacto', :p)"),
                {"p": p},
            ).scalar_one()
        for p in ("UPDATE", "DELETE", "TRUNCATE"):
            assert not c.execute(
                text("select has_table_privilege('climasense_app', 'silver.inferencias_impacto', :p)"),
                {"p": p},
            ).scalar_one()
        assert c.execute(
            text("select has_table_privilege('climasense_app', 'gold.previsoes_impacto', 'SELECT')")
        ).scalar_one()


def test_0025_sobe_e_desce_somente_em_banco_descartavel():
    from alembic import command

    from tests.conftest import URL_TESTE, _alembic, recriar_banco

    engine = recriar_banco(URL_TESTE)
    try:
        command.downgrade(_alembic(URL_TESTE), "0024")
        with engine.connect() as c:
            assert c.execute(text("select to_regclass('silver.inferencias_impacto')")).scalar_one() is None
            assert c.execute(text("select to_regclass('gold.previsoes_impacto')")).scalar_one() is None
        command.upgrade(_alembic(URL_TESTE), "head")
        with engine.connect() as c:
            assert c.execute(text("select to_regclass('gold.previsoes_impacto')")).scalar_one()
    finally:
        engine.dispose()


def test_persistencia_sobrevive_nova_sessao_local(engine_teste, monkeypatch):
    from climasense.infra.postgres import fabrica_sessoes
    from climasense.ml.alagamento import armazenamento
    from tests.conftest import URL_TESTE, recriar_banco

    monkeypatch.setattr(armazenamento, "carregar_em_cache", lambda: None)
    fabrica = fabrica_sessoes(engine_teste)
    try:
        with fabrica() as db:
            carga.sincronizar_territorios(db, carga.geo_local())
            db.commit()
            resultado = analisar(db, AGORA, 24)
            assert persistir(db, resultado) == 188
        with fabrica() as outra:
            assert outra.execute(text("select count(*) from gold.previsoes_impacto")).scalar_one() == 188
            assert persistir(outra, resultado) == 0
    finally:
        # Só o banco descartável explícito do runner, jamais URL da aplicação.
        recriar_banco(URL_TESTE).dispose()
