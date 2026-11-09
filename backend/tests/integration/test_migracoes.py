import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from tests.conftest import precisa_postgres

pytestmark = [precisa_postgres, pytest.mark.integracao]

TABELAS = {
    "app": {
        "usuarios",
        "sessoes",
        "tentativas_login",
        "liberacoes_login",
        "territorios",
        "fontes",
        "etl_execucoes",
        "avaliacoes",
        "avaliacao_versoes",
        "comunicados",
        "comunicado_versoes",
        "revisoes",
        "auditoria",
        "estagio_parametros",
        "estagio_declaracoes",
        "estagio_oficial",
        "cenarios",
        "acoes_resposta",
        "acao_eventos",
        "eventos_chuva",
        "evento_chuva_itens",
    },
    "silver": {
        "estacoes",
        "observacoes",
        "ocorrencias",
        "previsoes_emitidas",
        "apac_chuva_leituras",
        "apac_chuva_diaria",
        "alertas_oficiais",
        "infodengue_semanal",
        "leptospirose_semanal",
        "arboviroses_bairro_ano",
        "equipamentos_saude",
        "populacao_bairro",
        "areas_risco",
        "suscetibilidade_deslizamento",
        "atendimentos_grau_risco",
        "alagamento_2026",
        # 0020 (hidrologia)
        "rios_estacoes",
        "rios_leituras",
        "reservatorios",
        "reservatorios_leituras",
        "rio_referencia_territorio",
        # 0021 (meteorologia observada e de modelo)
        "apac_chuva_passos",
        "apac_estacoes_cadastro",
        "solo_modelo_horario",
        "solo_modelo_diario",
        "apac_previsao_horaria",
        "apac_tendencia_chuva",
        "apac_radar",
        # 0023 (saúde durante o evento e histórico de desastres)
        "samu_demanda_semana",
        "agua_vigilancia_semana",
        "desastres_atlas",
    },
    "gold": {
        "chuva_diaria",
        "chuva_mensal",
        "referencia_mensal",
        "chuva_apac_agora",
        "chuva_apac_diaria",
        "alagamento_bairro_dia",
        "ocorrencias_bairro",
        "saude_semanal",
        "arboviroses_bairro_ano",
        "indicador_territorial",
        "cobertura_indicador",
        "rio_situacao",
        "reservatorio_situacao",
        "chuva_obs_hora_distrito",
        "chuva_obs_72h_distrito",
        "estacoes_chuva_status",
        "solo_modelo_distrito",
        # 0023
        "samu_demanda_semana",
        "agua_vigilancia_semana",
        "desastres_historico",
    },
}


def test_migracoes_criam_todas_as_tabelas(engine_teste):
    with engine_teste.connect() as c:
        for esquema, esperadas in TABELAS.items():
            reais = set(
                c.execute(
                    text("select tablename from pg_tables where schemaname = :e"), {"e": esquema}
                ).scalars()
            )
            assert reais == esperadas, esquema
        # dados individuais de vacinação foram apagados (0013, RNF-03)
        assert not c.execute(
            text(
                "select 1 from information_schema.tables where table_name in "
                "('silver_vacinados', 'vacinados', 'silver_vacinados_legado_etl_avd', 'gold_previsoes')"
            )
        ).all()


def _usuario(sessao, email):
    return sessao.execute(
        text(
            "insert into app.usuarios (nome, email, senha_hash, papeis) values (:n, :e, 'x', '{analista}') returning id"
        ),
        {"n": email.split("@")[0], "e": email},
    ).scalar_one()


def _territorio(sessao):
    sessao.execute(
        text(
            "insert into app.territorios values ('ds-5','distrito','DS V','Distrito Sanitário V',null,'5') on conflict do nothing"
        )
    )


def test_email_precisa_ser_minusculo_e_unico(sessao):
    _usuario(sessao, "ana@recife.pe.gov.br")
    with pytest.raises(IntegrityError), sessao.begin_nested():
        _usuario(sessao, "ana@recife.pe.gov.br")
    with pytest.raises(IntegrityError), sessao.begin_nested():
        _usuario(sessao, "Ana@Recife.pe.gov.br")


def test_papel_invalido_e_recusado(sessao):
    with pytest.raises(IntegrityError):
        sessao.execute(
            text("insert into app.usuarios (nome,email,senha_hash,papeis) values ('x','x@y.z','h','{dono}')")
        )


def test_rn05_autor_nao_revisa_a_propria_versao_no_banco(sessao):
    autor = _usuario(sessao, "autor@recife.pe.gov.br")
    revisor = _usuario(sessao, "revisor@recife.pe.gov.br")
    _territorio(sessao)
    av = sessao.execute(
        text(
            "insert into app.avaliacoes (territorio_id, periodo_inicio, periodo_fim, estado, criado_por) "
            "values ('ds-5','2026-10-01','2026-10-15','em_revisao',:a) returning id"
        ),
        {"a": autor},
    ).scalar_one()
    versao = sessao.execute(
        text(
            "insert into app.avaliacao_versoes (avaliacao_id, numero, prioridade, justificativa, autor_id) "
            "values (:av, 1, 'atencao', 'Justificativa', :a) returning id"
        ),
        {"av": av, "a": autor},
    ).scalar_one()
    with pytest.raises(DBAPIError, match="RN-05"):
        with sessao.begin_nested():
            sessao.execute(
                text(
                    "insert into app.revisoes (alvo, versao_id, revisor_id, decisao) values ('avaliacao', :v, :r, 'aprovar')"
                ),
                {"v": versao, "r": autor},
            )
    sessao.execute(
        text(
            "insert into app.revisoes (alvo, versao_id, revisor_id, decisao) values ('avaliacao', :v, :r, 'aprovar')"
        ),
        {"v": versao, "r": revisor},
    )
    with pytest.raises(IntegrityError):  # devolver sem justificativa
        sessao.execute(
            text(
                "insert into app.revisoes (alvo, versao_id, revisor_id, decisao) values ('avaliacao', :v, :r, 'devolver')"
            ),
            {"v": versao, "r": revisor},
        )


def test_comunicado_publicado_precisa_ser_a_versao_aprovada(sessao):
    with pytest.raises(IntegrityError):
        sessao.execute(
            text(
                "insert into app.comunicados (estado, territorios, publico, nivel, validade_inicio, validade_fim, versao_atual, versao_aprovada) "
                "values ('publicado', '{ds-5}', 'populacao', 'alerta', now(), now() + interval '1 day', 2, 1)"
            )
        )


def test_valor_nulo_e_zero_sao_distintos_em_observacoes(sessao):
    sessao.execute(
        text(
            "insert into app.fontes (id,nome,orgao,url,tipo,conector,implementada) values "
            "('teste-real','Fonte','Órgão','https://exemplo','observada','x',true)"
        )
    )
    ex = sessao.execute(
        text("insert into app.etl_execucoes (fonte_id,status) values ('teste-real','sucesso') returning id")
    ).scalar_one()
    for valor in (None, 0.0):
        sessao.execute(
            text(
                "insert into silver.observacoes (fonte_id,variavel,valor,unidade,tipo,observado_em,coletado_em,execucao_id) "
                "values ('teste-real','chuva_mm',:v,'mm','observada',now(),now(),:e)"
            ),
            {"v": valor, "e": ex},
        )
    nulos, zeros = sessao.execute(
        text(
            "select count(*) filter (where valor is null), count(*) filter (where valor = 0) from silver.observacoes"
        )
    ).one()
    assert (nulos, zeros) == (1, 1)


def test_previsao_sem_horario_de_emissao_e_recusada(sessao):
    sessao.execute(
        text(
            "insert into app.fontes (id,nome,orgao,url,tipo,conector) values ('prev','F','O','https://x','prevista','x')"
        )
    )
    ex = sessao.execute(
        text("insert into app.etl_execucoes (fonte_id,status) values ('prev','sucesso') returning id")
    ).scalar_one()
    with pytest.raises(IntegrityError):
        sessao.execute(
            text(
                "insert into silver.observacoes (fonte_id,variavel,valor,unidade,tipo,observado_em,coletado_em,execucao_id) "
                "values ('prev','chuva_mm',1,'mm','prevista',now(),now(),:e)"
            ),
            {"e": ex},
        )


def test_id_gerado_pelo_banco_e_uuid(sessao):
    assert isinstance(_usuario(sessao, "uuid@recife.pe.gov.br"), uuid.UUID)
