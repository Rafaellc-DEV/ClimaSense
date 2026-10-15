"""Esquemas `silver` e `gold` + view de compatibilidade `public.silver_vacinados` (T2.4).

Revisão: 0002
Anterior: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

SQL = """
create schema if not exists silver;
create schema if not exists gold;

-- Vacinação: mesmas colunas produzidas pelo Transform do Projeto-ETL_AVD + rastreio da execução.
create table silver.vacinados (
  id bigserial primary key,
  faixa_etaria varchar(40),
  idade integer,
  sexo varchar(20),
  raca_cor varchar(40),
  municipio varchar(80),
  grupo varchar(160),
  categoria varchar(160),
  lote varchar(60),
  vacina varchar(120),
  dose numeric,
  data_vacinacao date not null,
  distrito_sanitario varchar(10),
  unidade_saude varchar(200),
  sistema_origem varchar(60),
  execucao_id uuid not null references app.etl_execucoes(id)
);
create index vacinados_execucao on silver.vacinados (execucao_id);
create index vacinados_distrito_data on silver.vacinados (distrito_sanitario, data_vacinacao);
-- O ETL antigo gravava public.silver_vacinados; a view mantém consultas e notebooks funcionando.
create view public.silver_vacinados as
  select faixa_etaria, idade, sexo, raca_cor, municipio, grupo, categoria, lote, vacina, dose,
         data_vacinacao, distrito_sanitario, unidade_saude, sistema_origem
  from silver.vacinados;

create table silver.estacoes (
  id varchar(80) primary key,
  fonte_id varchar(60) not null references app.fontes(id),
  codigo_fonte varchar(60) not null,
  nome varchar(160) not null,
  lat double precision not null check (lat between -90 and 90),
  lon double precision not null check (lon between -180 and 180),
  territorio_id varchar(80) references app.territorios(id),
  ativa boolean not null default true
);

-- Formato longo, com os metadados mínimos do contexto §16.2. valor nulo = sem dado (≠ 0, RN-02).
create table silver.observacoes (
  id bigserial primary key,
  fonte_id varchar(60) not null references app.fontes(id),
  estacao_id varchar(80) references silver.estacoes(id),
  territorio_id varchar(80) references app.territorios(id),
  variavel varchar(20) not null check (variavel in ('chuva_mm','nivel_m','mare_m','temp_c')),
  valor double precision,
  unidade varchar(10) not null,
  tipo varchar(10) not null check (tipo in ('observada','prevista','derivada')),
  observado_em timestamptz not null,
  emitido_em timestamptz,
  horizonte_h integer check (horizonte_h is null or horizonte_h between 0 and 240),
  coletado_em timestamptz not null,
  qualidade varchar(10) not null default 'ok' check (qualidade in ('ok','suspeito','ausente')),
  execucao_id uuid not null references app.etl_execucoes(id),
  constraint observacoes_previsao_tem_emissao check (tipo <> 'prevista' or emitido_em is not null)
);
create index observacoes_busca on silver.observacoes (variavel, territorio_id, observado_em);

create table silver.ocorrencias (
  id bigserial primary key,
  fonte_id varchar(60) not null references app.fontes(id),
  codigo_fonte varchar(80),
  territorio_id varchar(80) references app.territorios(id),
  ocorrido_em timestamptz,
  registrado_em timestamptz not null,
  tipo varchar(80) not null,
  confirmada boolean,
  precisao_espacial varchar(20) not null default 'bairro',
  execucao_id uuid not null references app.etl_execucoes(id)
);

create table silver.previsoes_emitidas (
  id bigserial primary key,
  territorio_id varchar(80) not null references app.territorios(id),
  horizonte_h integer not null check (horizonte_h in (24, 48, 72)),
  emitida_em timestamptz not null,
  metodo varchar(60) not null,
  versao_metodo varchar(20) not null,
  saida jsonb not null,
  insumos jsonb not null
);

create table gold.vacinacao_distrito_mes (
  distrito_codigo smallint not null check (distrito_codigo between 1 and 8),
  mes date not null,
  doses integer,
  amostra_n integer not null,
  total_fonte integer,
  suprimido boolean not null,
  execucao_id uuid not null references app.etl_execucoes(id),
  primary key (distrito_codigo, mes),
  constraint vacinacao_suprimido_sem_valor check (not suprimido or doses is null)
);

create table gold.chuva_diaria (
  territorio_id varchar(80) not null references app.territorios(id),
  dia date not null,
  acumulado_mm double precision,
  n_observacoes integer not null,
  cobertura_pct double precision not null check (cobertura_pct between 0 and 100),
  tipo varchar(10) not null,
  primary key (territorio_id, dia, tipo)
);

create table gold.chuva_mensal (
  territorio_id varchar(80) not null references app.territorios(id),
  mes date not null,
  acumulado_mm double precision,
  dias_com_dado integer not null,
  cobertura_pct double precision not null check (cobertura_pct between 0 and 100),
  tipo varchar(10) not null,
  primary key (territorio_id, mes, tipo)
);

create table gold.referencia_mensal (
  territorio_id varchar(80) not null references app.territorios(id),
  mes_do_ano smallint not null check (mes_do_ano between 1 and 12),
  media_mm double precision,
  mediana_mm double precision,
  anos_usados integer[] not null,
  cobertura_pct double precision not null,
  primary key (territorio_id, mes_do_ano)
);
"""


def upgrade() -> None:
    op.execute(SQL)


def downgrade() -> None:
    op.execute(
        "drop view if exists public.silver_vacinados; drop schema if exists gold cascade; drop schema if exists silver cascade;"
    )
