"""Migração 0022 e gravação dos conectores da cobertura territorial no Postgres de teste (RF-02, RF-04, RF-19).

As gravações dos conectores rodam dentro da transação da sessão de teste (desfeita ao fim): o banco volta limpo.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import pytest
from shapely.geometry import box, mapping
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from climasense.etl.conectores import alagamento_2026, atendimentos_grau, suscetibilidade
from climasense.etl.conectores.base import ExecucaoCtx
from tests.conftest import precisa_postgres

pytestmark = [precisa_postgres, pytest.mark.integracao]

AGORA = datetime(2026, 11, 6, 15, 0, tzinfo=UTC)
TABELAS_NOVAS = (
    "silver.suscetibilidade_deslizamento",
    "silver.atendimentos_grau_risco",
    "silver.alagamento_2026",
    "gold.indicador_territorial",
    "gold.cobertura_indicador",
)


class _Conexao:
    def __init__(self, c):
        self.c = c

    def __enter__(self):
        return self.c

    def __exit__(self, *a):
        return False


class EngineNaSessao:
    """`ctx.engine` que devolve a conexão da sessão de teste (nada é confirmado no banco)."""

    def __init__(self, sessao):
        self.sessao = sessao

    def begin(self):
        return _Conexao(self.sessao.connection())

    connect = begin


@pytest.fixture
def cx(sessao):
    for b in ("bairro-a", "bairro-b", "bairro-c"):
        sessao.execute(
            text("insert into app.territorios values (:i,'bairro',:i,:i,null,null) on conflict do nothing"),
            {"i": b},
        )
    ex = sessao.execute(
        text(
            "insert into app.etl_execucoes (fonte_id, status) values ('recife-alagamento-2026','sucesso') returning id"
        )
    ).scalar_one()
    return ExecucaoCtx(str(ex), None, None, EngineNaSessao(sessao), AGORA)


def _um(sessao, sql, **p):
    return sessao.execute(text(sql), p).all()


def test_migracao_registra_as_tres_fontes_implementadas_com_limites_em_anos(sessao):
    linhas = {
        r.id: r
        for r in sessao.execute(
            text(
                "select id, tipo, implementada, limite_desatualizacao_h, licenca from app.fontes where id in "
                "('sgb-suscetibilidade-deslizamento','recife-atendimentos-grau-risco','recife-alagamento-2026')"
            )
        )
    }
    assert set(linhas) == {
        "sgb-suscetibilidade-deslizamento",
        "recife-atendimentos-grau-risco",
        "recife-alagamento-2026",
    }
    assert all(r.implementada for r in linhas.values())
    assert linhas["sgb-suscetibilidade-deslizamento"].limite_desatualizacao_h == 43800
    assert linhas["recife-atendimentos-grau-risco"].limite_desatualizacao_h == 13140
    assert linhas["recife-alagamento-2026"].limite_desatualizacao_h == 8760
    assert "não declarada" in linhas["recife-alagamento-2026"].licenca


def test_papel_da_aplicacao_so_le_as_tabelas_novas(sessao):
    if not _um(sessao, "select 1 from pg_roles where rolname = 'climasense_app'"):
        pytest.skip("papel climasense_app ausente neste banco")
    for t in TABELAS_NOVAS:
        priv = {
            p: sessao.execute(
                text("select has_table_privilege('climasense_app', :t, :p)"), {"t": t, "p": p}
            ).scalar()
            for p in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE")
        }
        assert priv == {
            "SELECT": True,
            "INSERT": False,
            "UPDATE": False,
            "DELETE": False,
            "TRUNCATE": False,
        }, t


def test_restricoes_de_banco_recusam_fracao_grau_e_valor_invalidos(sessao):
    def insere(sql, **p):
        with pytest.raises(IntegrityError), sessao.begin_nested():
            sessao.execute(text(sql), p)

    insere(
        "insert into silver.suscetibilidade_deslizamento values ('bairro-a','alta',1,1.5,'sgb-suscetibilidade-deslizamento',null)"
    )
    insere(
        "insert into silver.suscetibilidade_deslizamento values ('bairro-a','muito-alta',1,0.5,'sgb-suscetibilidade-deslizamento',null)"
    )
    insere(
        "insert into silver.atendimentos_grau_risco values ('bairro-a',2024,'R5',1,'recife-atendimentos-grau-risco',null)"
    )
    insere(
        "insert into silver.atendimentos_grau_risco values ('bairro-a',2024,'R3',0,'recife-atendimentos-grau-risco',null)"
    )
    insere(
        "insert into silver.alagamento_2026 (id,camada,bairro_id,itens,fonte_id) values ('x','praca','bairro-a',1,'recife-alagamento-2026')"
    )
    insere(
        "insert into gold.indicador_territorial values ('bairro-a','i',-1,'u','r','p','recife-alagamento-2026',now())"
    )
    insere(  # fonte inexistente
        "insert into gold.indicador_territorial values ('bairro-a','i',1,'u','r','p','nao-existe',now())"
    )


def test_suscetibilidade_silver_e_gold_com_cobertura_e_bairro_sem_carta_sem_linha(sessao, cx):
    a, b = box(-34.90, -8.05, -34.89, -8.04), box(-34.88, -8.05, -34.87, -8.04)
    c = suscetibilidade.ConectorSgbSuscetibilidadeDeslizamento(
        http=None, malha=[("bairro-a", a), ("bairro-b", b), ("bairro-c", box(-34.80, -8.05, -34.79, -8.04))]
    )
    bruto = pd.DataFrame(
        [
            {
                "registro": "poligono",
                "classe": "Alta",
                "processo": "Deslizamento",
                "geometry": mapping(box(-34.90, -8.05, -34.895, -8.04)),
            },
            {
                "registro": "poligono",
                "classe": "Baixa",
                "processo": "Deslizamento",
                "geometry": mapping(box(-34.895, -8.05, -34.87, -8.04)),
            },
        ]
    )
    df = c.transformar(bruto, cx)
    assert c.gravar_silver(df, cx) == 8  # bairro-a e bairro-b, quatro classes cada; bairro-c sem carta
    c.gerar_gold(cx)
    gold = {
        (r.bairro_id, r.indicador): r
        for r in sessao.execute(
            text("select * from gold.indicador_territorial where fonte_id = :f"), {"f": c.id}
        )
    }
    alta_a = gold[("bairro-a", "suscetibilidade_deslizamento_alta")]
    assert alta_a.valor == pytest.approx(0.5, abs=0.001)
    assert alta_a.rotulo == "suscetibilidade do terreno (carta 2012–2014, escala 1:45.000)"
    assert alta_a.atualizado_em == AGORA and alta_a.unidade == "fracao_da_area_do_bairro"
    assert (
        gold[("bairro-b", "suscetibilidade_deslizamento_alta")].valor == 0
    )  # a carta cobre o bairro: zero medido
    assert not [k for k in gold if k[0] == "bairro-c"]  # sem carta: sem linha (nunca "baixa")
    cob = {r.indicador: r for r in sessao.execute(text("select * from gold.cobertura_indicador"))}
    k = cob["suscetibilidade_deslizamento_alta"]
    assert (k.bairros_com_dado, k.bairros_com_valor_positivo, k.bairros_total) == (2, 1, 3)
    assert "não é setor de risco" in k.observacao
    # recarga substitui, não duplica
    c.gravar_silver(df, cx)
    c.gerar_gold(cx)
    assert sessao.execute(text("select count(*) from silver.suscetibilidade_deslizamento")).scalar() == 8
    assert sessao.execute(text("select count(*) from gold.indicador_territorial")).scalar() == 8


def test_atendimentos_gold_tem_periodo_no_rotulo_e_zero_so_onde_ha_atendimento_com_grau(sessao, cx):
    c = atendimentos_grau.ConectorRecifeAtendimentosGrauRisco(http=None)
    df = pd.DataFrame(
        [
            {"bairro_id": "bairro-a", "ano": 2014, "grau": "R3", "atendimentos": 4},
            {"bairro_id": "bairro-a", "ano": 2024, "grau": "R4", "atendimentos": 1},
            {"bairro_id": "bairro-a", "ano": 2024, "grau": "R1", "atendimentos": 2},
            {"bairro_id": "bairro-b", "ano": 2024, "grau": "R1", "atendimentos": 7},
        ]
    )
    c.cobertura = {}
    assert c.gravar_silver(df, cx) == 4
    c.gerar_gold(cx)
    gold = {
        (r.bairro_id, r.indicador): r
        for r in sessao.execute(
            text("select * from gold.indicador_territorial where fonte_id = :f"), {"f": c.id}
        )
    }
    r34 = gold[("bairro-a", "atendimentos_grau_r3_r4")]
    assert (
        r34.valor == 5
        and r34.rotulo == "atendimentos com grau R3/R4 de 2014 a 2024"
        and r34.periodo == "2014-2024"
    )
    assert gold[("bairro-b", "atendimentos_grau_r3_r4")].valor == 0  # tem grau, nenhum R3/R4
    assert gold[("bairro-a", "atendimentos_grau_total")].valor == 7
    assert not [k for k in gold if k[0] == "bairro-c"]
    k = sessao.execute(
        text("select * from gold.cobertura_indicador where indicador = 'atendimentos_grau_r3_r4'")
    ).one()
    assert (k.bairros_com_dado, k.bairros_com_valor_positivo, k.bairros_total) == (2, 1, 3)
    assert "para em 2024" in k.observacao and "não é mapeamento de risco" in k.observacao


def test_alagamento_2026_gold_zero_medido_ausente_e_soma_so_do_que_existe(sessao, cx):
    c = alagamento_2026.ConectorRecifeAlagamento2026(http=None)
    linhas = [
        ("com-1", "comunidades", "bairro-a", "X", 4, 1, 0, None),
        ("com-2", "comunidades", "bairro-a", "Y", 4, 1, 12, None),
        (
            "com-3",
            "comunidades",
            "bairro-b",
            "Z",
            4,
            1,
            None,
            None,
        ),  # qtd_registros ausente: não soma, não é zero
        ("lotes-bairro-a", "lotes", "bairro-a", None, None, 30, None, 41),
        ("lotes-bairro-b", "lotes", "bairro-b", None, None, 2, None, None),  # sem qtdunhab: ausente
        ("trechos-bairro-a", "trechos", "bairro-a", None, None, 3, None, None),
    ]
    df = pd.DataFrame(
        linhas,
        columns=[
            "id", "camada", "bairro_id", "comunidade", "rpa", "itens", "qtd_registros", "unidades_habitacionais"
        ],
    )  # fmt: skip
    c.cobertura = {}
    assert c.gravar_silver(df, cx) == 6
    c.gerar_gold(cx)
    gold = {
        (r.bairro_id, r.indicador): r.valor
        for r in sessao.execute(
            text("select * from gold.indicador_territorial where fonte_id = :f"), {"f": c.id}
        )
    }
    assert gold[("bairro-a", "alagamento_2026_registros")] == 12
    assert ("bairro-b", "alagamento_2026_registros") not in gold  # todos os registros ausentes
    assert (
        gold[("bairro-a", "alagamento_2026_comunidades")] == 2
        and gold[("bairro-b", "alagamento_2026_lotes")] == 2
    )
    assert gold[("bairro-a", "alagamento_2026_unidades_habitacionais")] == 41
    assert ("bairro-b", "alagamento_2026_unidades_habitacionais") not in gold
    assert ("bairro-b", "alagamento_2026_trechos") not in gold and not [k for k in gold if k[0] == "bairro-c"]
    cob = {r.indicador: r for r in sessao.execute(text("select * from gold.cobertura_indicador"))}
    assert (
        cob["alagamento_2026_trechos"].bairros_com_dado == 1
        and cob["alagamento_2026_trechos"].bairros_total == 3
    )
    assert cob["alagamento_2026_lotes"].rotulo == "evento de 2026, sem data por registro"
    assert "sem data por registro" in cob["alagamento_2026_comunidades"].observacao
