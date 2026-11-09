"""Meteorologia observada e de modelo: chuva medida por hora e por distrito, acumulado de 72 h, umidade do solo,
temperatura prevista, tendência e radar da APAC (RF-12.10, RF-19, RN-01, RN-02, RN-11).

Só tabelas novas (nada do que existe é alterado) e três fontes novas em `app.fontes`:
- `open-meteo-solo` (modelo, Experimental), `open-meteo-temperatura` (previsão) e `apac-previsao` (previsão
  horária, tendência e radar da APAC).

silver
- `apac_chuva_passos`: leitura única de cada estação (`ultima_medicao`, a cada 10-15 min); a hora vem da fonte.
  `valor_mm` nulo = leitura sem valor (nunca zero).
- `apac_estacoes_cadastro`: `status_dados` e `tempo_min` do cadastro da APAC (estado atual por código).
- `solo_modelo_horario` (previsão e horas recentes do modelo) e `solo_modelo_diario` (histórico ERA5-Land do
  próprio ponto, média diária): tudo é MODELO, nunca medida.
- `apac_previsao_horaria`, `apac_tendencia_chuva`, `apac_radar`: só guarda dado, URL e hora (sem baixar imagem).

gold (recalculadas só por SQL a partir da silver, como as demais)
- `chuva_obs_hora_distrito`, `chuva_obs_72h_distrito`, `estacoes_chuva_status` e `solo_modelo_distrito`.

O papel `climasense_app` só tem SELECT nas tabelas novas (o ETL é quem grava).

Revisão: 0021
Anterior: a mais recente abaixo de 0021 que existir na pasta (0020 quando estiver presente)
"""

from pathlib import Path

from alembic import op


def _anterior() -> str:
    """Última revisão numerada abaixo de 0021: a 0020 é de outra frente e pode chegar depois; assim esta migração
    nunca cria uma segunda cabeça."""
    numeros = sorted(
        p.name[:4] for p in Path(__file__).parent.glob("[0-9][0-9][0-9][0-9]_*.py") if p.name[:4] < "0021"
    )
    return numeros[-1]


revision = "0021"
down_revision = _anterior()
branch_labels = None
depends_on = None

PAPEL = "climasense_app"

TABELAS_SILVER = (
    "apac_chuva_passos",
    "apac_estacoes_cadastro",
    "solo_modelo_horario",
    "solo_modelo_diario",
    "apac_previsao_horaria",
    "apac_tendencia_chuva",
    "apac_radar",
)
TABELAS_GOLD = (
    "chuva_obs_hora_distrito",
    "chuva_obs_72h_distrito",
    "estacoes_chuva_status",
    "solo_modelo_distrito",
)
FONTES_NOVAS = ("open-meteo-solo", "open-meteo-temperatura", "apac-previsao")

SQL = """
create table silver.apac_chuva_passos (
  id bigserial primary key,
  estacao_id varchar(80) not null references silver.estacoes(id),
  lida_em timestamptz not null,
  valor_mm double precision check (valor_mm is null or valor_mm >= 0),
  coletado_em timestamptz not null,
  visto_em timestamptz not null,
  execucao_id uuid not null references app.etl_execucoes(id),
  constraint apac_passo_unico unique (estacao_id, lida_em)
);
create index apac_passos_recentes on silver.apac_chuva_passos (lida_em desc);

create table silver.apac_estacoes_cadastro (
  codigo_fonte varchar(60) primary key,
  nome varchar(160),
  status_dados varchar(40),
  tempo_min bigint check (tempo_min is null or tempo_min >= 0),
  ultima_leitura_em timestamptz,
  visto_em timestamptz not null,
  execucao_id uuid not null references app.etl_execucoes(id)
);

create table silver.solo_modelo_horario (
  territorio_id varchar(80) not null references app.territorios(id),
  camada varchar(10) not null check (camada in ('0_7cm', '7_28cm')),
  observado_em timestamptz not null,
  valor_m3m3 double precision check (valor_m3m3 is null or (valor_m3m3 >= 0 and valor_m3m3 <= 1)),
  emitido_em timestamptz not null,
  coletado_em timestamptz not null,
  execucao_id uuid not null references app.etl_execucoes(id),
  primary key (territorio_id, camada, observado_em)
);

create table silver.solo_modelo_diario (
  territorio_id varchar(80) not null references app.territorios(id),
  camada varchar(10) not null check (camada in ('0_7cm', '7_28cm')),
  dia date not null,
  media_m3m3 double precision not null check (media_m3m3 >= 0 and media_m3m3 <= 1),
  n_horas smallint not null check (n_horas between 1 and 24),
  coletado_em timestamptz not null,
  execucao_id uuid not null references app.etl_execucoes(id),
  primary key (territorio_id, camada, dia)
);

create table silver.apac_previsao_horaria (
  hora_prevista timestamptz primary key,
  temperatura_c double precision,
  umidade_pct double precision check (umidade_pct is null or umidade_pct between 0 and 100),
  precipitacao_mm double precision check (precipitacao_mm is null or precipitacao_mm >= 0),
  codigo_recebido integer not null,
  coletado_em timestamptz not null,
  execucao_id uuid not null references app.etl_execucoes(id)
);

create table silver.apac_tendencia_chuva (
  mesorregiao varchar(60) not null,
  dia date not null,
  categoria varchar(60) not null,
  faixa_mm varchar(40),
  atualizado_em timestamptz,
  coletado_em timestamptz not null,
  execucao_id uuid not null references app.etl_execucoes(id),
  primary key (mesorregiao, dia)
);

create table silver.apac_radar (
  data_referencia timestamptz primary key,
  lat double precision not null,
  lon double precision not null,
  url_acumulado_1h text,
  url_acumulado_24h text,
  url_cappi_1km text,
  coletado_em timestamptz not null,
  execucao_id uuid not null references app.etl_execucoes(id)
);

-- Hora local sem leitura não tem linha (lacuna, nunca zero). Valores = soma das leituras medidas da hora.
create table gold.chuva_obs_hora_distrito (
  territorio_id varchar(80) not null references app.territorios(id),
  hora_inicio timestamptz not null,
  chuva_max_mm double precision,
  chuva_mediana_mm double precision,
  n_estacoes integer not null,
  n_com_leitura integer not null,
  n_completas integer not null,
  primeira_leitura_em timestamptz not null,
  ultima_leitura_em timestamptz not null,
  estacoes text[] not null,
  primary key (territorio_id, hora_inicio)
);

create table gold.chuva_obs_72h_distrito (
  territorio_id varchar(80) not null references app.territorios(id),
  nivel varchar(10) not null,
  status varchar(20) not null check (status in ('com_leitura', 'sem_leitura', 'sem_pluviometro')),
  chuva_72h_max_mm double precision,
  chuva_72h_mediana_mm double precision,
  n_estacoes integer not null,
  n_com_leitura integer not null,
  n_sem_leitura integer not null,
  lida_em timestamptz,
  referencia_em timestamptz,
  estacoes text[] not null,
  primary key (territorio_id)
);

create table gold.estacoes_chuva_status (
  estacao_id varchar(80) primary key references silver.estacoes(id),
  nome varchar(160) not null,
  distrito_id varchar(80) not null references app.territorios(id),
  bairro_id varchar(80) references app.territorios(id),
  situacao varchar(20) not null check (situacao in ('com_leitura', 'leitura_antiga', 'sem_valor')),
  lida_em timestamptz,
  referencia_em timestamptz,
  status_dados varchar(40),
  tempo_min bigint
);

create table gold.solo_modelo_distrito (
  territorio_id varchar(80) not null references app.territorios(id),
  camada varchar(10) not null,
  referencia_em timestamptz not null,
  valor_24h_m3m3 double precision,
  n_horas integer not null,
  percentil double precision,
  p25_m3m3 double precision,
  p75_m3m3 double precision,
  p90_m3m3 double precision,
  n_historico_dias integer not null,
  classe varchar(12) check (classe in ('seco', 'normal', 'umido', 'muito_umido')),
  natureza varchar(10) not null,
  selo varchar(12) not null,
  primary key (territorio_id, camada)
);
"""

FONTES = [
    # id, nome, órgão, url, tipo, licença, conector, limite_h, min_obs
    (
        "open-meteo-solo",
        "Umidade do solo estimada por modelo (0-7 cm e 7-28 cm)",
        "Open-Meteo / ECMWF (IFS e ERA5-Land)",
        "https://open-meteo.com/en/docs",
        "derivada",
        "CC BY 4.0",
        "ConectorOpenMeteoSolo",
        6,
        1,
    ),
    (
        "open-meteo-temperatura",
        "Temperatura do ar prevista por modelo (2 m)",
        "Open-Meteo",
        "https://open-meteo.com/en/docs",
        "prevista",
        "CC BY 4.0",
        "ConectorOpenMeteoTemperatura",
        6,
        1,
    ),
    (
        "apac-previsao",
        "Previsão horária do Recife, tendência de chuva e radar (APAC)",
        "APAC — Agência Pernambucana de Águas e Clima",
        "https://api.apac.pe.gov.br/api.php",
        "prevista",
        None,
        "ConectorApacPrevisao",
        2,
        1,
    ),
]

GRANTS = f"""
do $$
begin
  if exists (select 1 from pg_roles where rolname = '{PAPEL}') then
    {"".join(f"execute 'grant select on silver.{t} to {PAPEL}'; " for t in TABELAS_SILVER)}
    {"".join(f"execute 'grant select on gold.{t} to {PAPEL}'; " for t in TABELAS_GOLD)}
    {"".join(f"execute 'revoke insert, update, delete, truncate on silver.{t} from {PAPEL}'; " for t in TABELAS_SILVER)}
    {"".join(f"execute 'revoke insert, update, delete, truncate on gold.{t} from {PAPEL}'; " for t in TABELAS_GOLD)}
  end if;
end $$;
"""


def upgrade() -> None:
    from sqlalchemy import text

    op.execute(SQL)
    conexao = op.get_bind()
    for f in FONTES:
        conexao.execute(
            text(
                "insert into app.fontes (id, nome, orgao, url, tipo, licenca, conector, limite_desatualizacao_h, "
                "min_observacoes, implementada) values (:a,:b,:c,:d,:e,:f,:g,:h,:i, true) "
                "on conflict (id) do update set nome = excluded.nome, orgao = excluded.orgao, url = excluded.url, "
                "tipo = excluded.tipo, licenca = excluded.licenca, conector = excluded.conector, "
                "limite_desatualizacao_h = excluded.limite_desatualizacao_h, "
                "min_observacoes = excluded.min_observacoes, implementada = true"
            ),
            dict(zip("abcdefghi", f, strict=True)),
        )
    op.execute(GRANTS)


def downgrade() -> None:
    for t in TABELAS_GOLD:
        op.execute(f"drop table if exists gold.{t}")
    for t in reversed(TABELAS_SILVER):
        op.execute(f"drop table if exists silver.{t}")
    lista = ", ".join(f"'{f}'" for f in FONTES_NOVAS)
    op.execute(f"delete from app.etl_execucoes where fonte_id in ({lista})")
    op.execute(f"delete from app.fontes where id in ({lista})")
