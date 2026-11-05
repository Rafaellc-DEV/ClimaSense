"""Fontes reais do foco em chuvas (specs/foco-chuvas.md): pluviômetros da APAC, alertas oficiais, ocorrências de
alagamento da Defesa Civil e abrigos dos Dados Abertos.

- silver.apac_chuva_leituras: acumulados (1 h … 120 h) de cada estação no instante da última leitura;
- silver.apac_chuva_diaria: chuva diária por estação (histórico mensal da APAC, desde 2022);
- gold.chuva_apac_agora / gold.chuva_apac_diaria: por bairro, distrito e Recife (máximo e mediana entre
  estações; bairro sem estação herda do distrito, marcado em `herdado_de`, RN-07);
- silver.alertas_oficiais: avisos da APAC, INMET, Cemaden e IDAP (CAP) que atingem o Recife;
- gold.alagamento_bairro_dia: atendimentos de alagamento por bairro e dia (rótulo fraco, ver dicionário);
- app.abrigos ganha fonte_url, fonte_data, tipo_local, capacidade_fonte, status_origem e status_lido_em
  (carga `recife-abrigos`: Dados Abertos, lista curada e feed "Abrigos Ativos" do COP).

Revisão: 0008
Anterior: 0007
"""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

SQL = """
create table silver.apac_chuva_leituras (
  id bigserial primary key,
  estacao_id varchar(80) not null references silver.estacoes(id),
  lida_em timestamptz not null,
  janela_h smallint not null check (janela_h in (1, 3, 6, 12, 24, 48, 72, 96, 120)),
  valor_mm double precision check (valor_mm is null or valor_mm >= 0),
  coletado_em timestamptz not null,
  visto_em timestamptz not null,
  execucao_id uuid not null references app.etl_execucoes(id),
  constraint apac_leitura_unica unique (estacao_id, lida_em, janela_h)
);
create index apac_leituras_recentes on silver.apac_chuva_leituras (lida_em desc);

create table silver.apac_chuva_diaria (
  estacao_id varchar(80) not null references silver.estacoes(id),
  dia date not null,
  valor_mm double precision check (valor_mm is null or valor_mm >= 0),
  valor_bruto_mm double precision,
  qualidade varchar(12) not null default 'ok' check (qualidade in ('ok', 'ausente', 'falha', 'suspeito')),
  coletado_em timestamptz not null,
  execucao_id uuid not null references app.etl_execucoes(id),
  primary key (estacao_id, dia)
);

create table gold.chuva_apac_agora (
  territorio_id varchar(80) not null references app.territorios(id),
  nivel varchar(10) not null,
  chuva_24h_max_mm double precision,
  chuva_24h_mediana_mm double precision,
  chuva_1h_max_mm double precision,
  n_estacoes integer not null,
  n_atualizadas integer not null,
  lida_em timestamptz,
  referencia_em timestamptz,
  herdado_de varchar(80),
  estacoes text[] not null,
  primary key (territorio_id)
);

create table gold.chuva_apac_diaria (
  territorio_id varchar(80) not null references app.territorios(id),
  dia date not null,
  nivel varchar(10) not null,
  max_mm double precision,
  mediana_mm double precision,
  n_estacoes integer not null,
  herdado_de varchar(80),
  primary key (territorio_id, dia)
);

create table silver.alertas_oficiais (
  id bigserial primary key,
  origem varchar(10) not null check (origem in ('apac', 'inmet', 'cemaden', 'idap')),
  codigo_fonte varchar(120) not null,
  evento varchar(200) not null,
  nivel varchar(10) check (nivel in ('amarelo', 'laranja', 'vermelho')),
  nivel_original varchar(60),
  emitido_em timestamptz,
  inicio_em timestamptz,
  expira_em timestamptz,
  url text,
  descricao text,
  area varchar(300),
  criterio_geo varchar(10) not null check (criterio_geo in ('geocode', 'poligono', 'regiao')),
  territorio_id varchar(80) not null default 'recife' references app.territorios(id),
  primeira_vez_em timestamptz not null,
  visto_em timestamptz not null,
  execucao_id uuid not null references app.etl_execucoes(id),
  constraint alerta_oficial_unico unique (origem, codigo_fonte)
);
create index alertas_oficiais_vigencia on silver.alertas_oficiais (expira_em desc);

create index ocorrencias_fonte_territorio on silver.ocorrencias (fonte_id, territorio_id, registrado_em);

create table gold.alagamento_bairro_dia (
  territorio_id varchar(80) not null references app.territorios(id),
  distrito_id varchar(80) references app.territorios(id),
  dia date not null,
  registros integer not null,
  primary key (territorio_id, dia)
);

alter table app.abrigos add column fonte_url text;
alter table app.abrigos add column fonte_data date;
alter table app.abrigos add column tipo_local varchar(40);
-- capacidade informada pela fonte (a coluna `capacidade` continua sendo da equipe)
alter table app.abrigos add column capacidade_fonte integer check (capacidade_fonte >= 0);
-- de onde veio o último `aberto` automático: feed "Abrigos Ativos" do COP Recife (a equipe continua
-- registrando pelo PATCH; o que ela informa depois da leitura do COP prevalece)
alter table app.abrigos add column status_origem varchar(10) check (status_origem in ('manual', 'cop'));
alter table app.abrigos add column status_lido_em timestamptz;
"""

FONTES = [
    # id, nome, órgão, url, tipo, licença, conector, limite_h, min_obs
    (
        "apac-chuva",
        "Chuva observada nos pluviômetros do Recife (APAC + Cemaden)",
        "APAC — Agência Pernambucana de Águas e Clima",
        "https://api.apac.pe.gov.br/api.php",
        "observada",
        None,
        "ConectorApacChuva",
        2,
        5,
    ),
    (
        "alertas-oficiais",
        "Avisos oficiais que atingem o Recife (APAC, INMET, Cemaden, IDAP)",
        "APAC / INMET / Cemaden / Defesa Civil Nacional",
        "https://idapfile.mdr.gov.br/idap/api/rss/cap",
        "observada",
        None,
        "ConectorAlertasOficiais",
        2,
        1,
    ),
    (
        "recife-alagamento",
        "Atendimentos de alagamento da Defesa Civil (por bairro e dia)",
        "Prefeitura do Recife (Dados Abertos)",
        "https://dados.recife.pe.gov.br/dataset/registro-de-atendimentos-da-defesa-civil",
        "observada",
        "ODbL",
        "ConectorRecifeAlagamento",
        24 * 365,
        30,
    ),
    (
        "recife-abrigos",
        "Abrigos e pontos de apoio (Ação Inverno)",
        "Prefeitura do Recife (Dados Abertos)",
        "https://dados.recife.pe.gov.br/dataset/abrigos-temporarios-disponiveis",
        "observada",
        "ODbL",
        "ConectorRecifeAbrigos",
        24 * 365,
        1,
    ),
]


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
                "licenca = excluded.licenca, conector = excluded.conector, "
                "limite_desatualizacao_h = excluded.limite_desatualizacao_h, "
                "min_observacoes = excluded.min_observacoes, implementada = true"
            ),
            dict(zip("abcdefghi", f, strict=True)),
        )


def downgrade() -> None:
    op.execute(
        """
        alter table app.abrigos drop column if exists status_lido_em;
        alter table app.abrigos drop column if exists status_origem;
        alter table app.abrigos drop column if exists capacidade_fonte;
        alter table app.abrigos drop column if exists tipo_local;
        alter table app.abrigos drop column if exists fonte_data;
        alter table app.abrigos drop column if exists fonte_url;
        drop table if exists gold.alagamento_bairro_dia;
        drop index if exists silver.ocorrencias_fonte_territorio;
        drop table if exists silver.alertas_oficiais;
        drop table if exists gold.chuva_apac_diaria;
        drop table if exists gold.chuva_apac_agora;
        drop table if exists silver.apac_chuva_diaria;
        drop table if exists silver.apac_chuva_leituras;
        update app.fontes set implementada = false where id in ('apac-chuva', 'recife-alagamento');
        delete from app.fontes f where f.id in ('alertas-oficiais', 'recife-abrigos')
          and not exists (select 1 from app.etl_execucoes e where e.fonte_id = f.id);
        """
    )
