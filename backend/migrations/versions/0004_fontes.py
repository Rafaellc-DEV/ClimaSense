"""Registro das fontes reais (implementadas e planejadas) — T5.9.

Revisão: 0004
Anterior: 0003
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

FONTES = [
    # id, nome, órgão, url, tipo, licença, conector, limite_h, min_obs, implementada
    (
        "territorio-oficial",
        "Distritos sanitários, bairros e faixas hídricas",
        "Prefeitura do Recife (Dados Abertos)",
        "https://dados.recife.pe.gov.br/dataset/distritos-sanitarios",
        "observada",
        "ODbL",
        "territorio.carga",
        24 * 365,
        1,
        True,
    ),
    (
        "vacinacao",
        "Perfil das pessoas vacinadas — COVID-19",
        "Prefeitura do Recife (Dados Abertos)",
        "https://dados.recife.pe.gov.br/dataset/perfil-das-pessoas-vacinadas-covid-19",
        "observada",
        "ODbL",
        "ConectorVacinacao",
        24 * 31,
        30,
        True,
    ),
    (
        "open-meteo-historico",
        "Chuva horária por distrito (reanálise ERA5)",
        "Open-Meteo / Copernicus ECMWF",
        "https://open-meteo.com/en/docs/historical-weather-api",
        "derivada",
        "CC BY 4.0",
        "ConectorOpenMeteoHistorico",
        24 * 8,
        365,
        True,
    ),
    (
        "open-meteo-previsao",
        "Chuva prevista por distrito (até 72 h)",
        "Open-Meteo",
        "https://open-meteo.com/en/docs",
        "prevista",
        "CC BY 4.0",
        "ConectorOpenMeteoPrevisao",
        6,
        24,
        True,
    ),
    (
        "open-meteo-mare",
        "Nível do mar previsto em frente ao Recife (inclui a maré)",
        "Open-Meteo Marine",
        "https://open-meteo.com/en/docs/marine-weather-api",
        "prevista",
        "CC BY 4.0",
        "ConectorOpenMeteoMare",
        24,
        24,
        True,
    ),
    (
        "recife-alagamento",
        "Ocorrências de alagamento (Defesa Civil)",
        "Prefeitura do Recife (Dados Abertos)",
        "https://dados.recife.pe.gov.br/dataset?tags=alagamento",
        "observada",
        None,
        "ConectorRecifeAlagamento",
        24,
        30,
        False,
    ),
    (
        "ana-telemetria",
        "Chuva e nível de rios (estações telemétricas)",
        "ANA — HidroWebService",
        "https://www.gov.br/ana/pt-br",
        "observada",
        None,
        "ConectorAnaTelemetria",
        6,
        24,
        False,
    ),
    (
        "apac-chuva",
        "Chuva acumulada em 24 h",
        "APAC",
        "https://www.apac.pe.gov.br/monitoramento",
        "observada",
        None,
        "ConectorApacChuva",
        6,
        24,
        False,
    ),
    (
        "inmet",
        "Estação automática Recife (A301)",
        "INMET",
        "https://portal.inmet.gov.br",
        "observada",
        None,
        "ConectorInmet",
        6,
        24,
        False,
    ),
    (
        "cemaden",
        "Pluviômetros automáticos",
        "Cemaden",
        "https://www.gov.br/cemaden",
        "observada",
        None,
        "ConectorCemaden",
        6,
        24,
        False,
    ),
    (
        "mare-marinha",
        "Tábua de maré oficial do Porto do Recife",
        "Marinha do Brasil — CHM",
        "https://www.marinha.mil.br/chm/tabuas-de-mare",
        "prevista",
        None,
        "ConectorMareMarinha",
        24 * 31,
        1,
        False,
    ),
]


def upgrade() -> None:
    from sqlalchemy import text

    conexao = op.get_bind()
    for f in FONTES:
        conexao.execute(
            text(
                "insert into app.fontes (id, nome, orgao, url, tipo, licenca, conector, limite_desatualizacao_h, min_observacoes, "
                "implementada) values (:a,:b,:c,:d,:e,:f,:g,:h,:i,:j) on conflict (id) do nothing"
            ),
            dict(zip("abcdefghij", f, strict=True)),
        )


def downgrade() -> None:
    op.execute("delete from app.fontes where id in (" + ",".join(f"'{f[0]}'" for f in FONTES) + ")")
