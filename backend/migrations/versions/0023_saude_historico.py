"""Saúde durante o evento e histórico de desastres: SAMU Recife, SISAGUA e Atlas Digital de Desastres.

Só tabelas novas (silver e gold) e três linhas em `app.fontes`. Nada existente é alterado.

- `silver.samu_demanda_semana`: chamados de urgência do SAMU por semana epidemiológica (domingo), bairro escrito na
  fonte e grupo (diarreia, desidratação, febre, mialgia e afins, mais `total`). SOMENTE contagens: endereço, sexo,
  idade e hora do atendimento nunca chegam ao banco (RN-13). `territorio_id` nulo quando o bairro não casa.
- `silver.agua_vigilancia_semana`: análises de E. coli e de cloro residual por semana, bairro e motivo (rotina ou
  dirigida): contagens, sem percentual (RN-06).
- `silver.desastres_atlas`: eventos do Recife no Atlas Digital de Desastres (protocolo S2iD, data, tipologia, status,
  danos humanos e materiais). Campo vazio é nulo; 0 é o que o município informou (a fonte não distingue).
- `gold.samu_demanda_semana`, `gold.agua_vigilancia_semana`, `gold.desastres_historico`: gerados só por SQL; bairro,
  distrito e município. A contagem do SAMU fica inteira na gold; a supressão de 1 a 4 acontece ao servir (RNF-03).
- `climasense_app`: só SELECT nas seis tabelas (a gravação é do ETL).
- app.fontes: `samu-recife`, `sisagua`, `atlas-desastres`.

Revisão: 0023
Anterior: a mais recente abaixo de 0023 que existir na pasta (0022 quando estiver presente)
"""

from pathlib import Path

from alembic import op


def _anterior() -> str:
    """Última revisão numerada abaixo de 0023: a 0020 a 0022 são de outras frentes e podem chegar depois; assim
    esta migração nunca cria uma segunda cabeça."""
    numeros = sorted(
        p.name[:4] for p in Path(__file__).parent.glob("[0-9][0-9][0-9][0-9]_*.py") if p.name[:4] < "0023"
    )
    return numeros[-1]


revision = "0023"
down_revision = _anterior()
branch_labels = None
depends_on = None

PAPEL = "climasense_app"
SILVER = ("samu_demanda_semana", "agua_vigilancia_semana", "desastres_atlas")
GOLD = ("samu_demanda_semana", "agua_vigilancia_semana", "desastres_historico")

SQL = """
create table silver.samu_demanda_semana (
  inicio date not null check (extract(dow from inicio) = 0),
  bairro_fonte varchar(120) not null,
  territorio_id varchar(80) references app.territorios(id),
  grupo varchar(30) not null check (grupo in ('total', 'diarreia', 'infeccao_gastrointestinal', 'vomitos',
    'desidratacao', 'febre', 'mialgia', 'sindrome_viral')),
  chamados integer not null check (chamados > 0),
  incompleta boolean not null,
  primeiro_dia_dado date not null,
  ultimo_dia_dado date not null,
  fonte_atualizada_em date,
  coletado_em timestamptz not null,
  execucao_id uuid not null references app.etl_execucoes(id),
  primary key (inicio, bairro_fonte, grupo)
);
create index samu_demanda_territorio on silver.samu_demanda_semana (territorio_id, inicio);

create table silver.agua_vigilancia_semana (
  inicio date not null check (extract(dow from inicio) = 0),
  bairro_fonte varchar(120) not null,
  territorio_id varchar(80) references app.territorios(id),
  motivo_grupo varchar(10) not null check (motivo_grupo in ('rotina', 'dirigida')),
  analises_ecoli integer not null check (analises_ecoli >= 0),
  ecoli_presente integer not null check (ecoli_presente >= 0),
  analises_cloro integer not null check (analises_cloro >= 0),
  cloro_fora_padrao integer not null check (cloro_fora_padrao >= 0),
  incompleta boolean not null,
  ultima_coleta date not null,
  ultimo_registro date not null,
  coletado_em timestamptz not null,
  execucao_id uuid not null references app.etl_execucoes(id),
  primary key (inicio, bairro_fonte, motivo_grupo),
  check (ecoli_presente <= analises_ecoli and cloro_fora_padrao <= analises_cloro)
);
create index agua_vigilancia_territorio on silver.agua_vigilancia_semana (territorio_id, inicio);

create table silver.desastres_atlas (
  protocolo varchar(60) primary key,
  data_evento date not null,
  data_registro date,
  cobrade varchar(10),
  tipologia varchar(120),
  status varchar(30),
  mortos integer check (mortos is null or mortos >= 0),
  feridos integer check (feridos is null or feridos >= 0),
  desabrigados integer check (desabrigados is null or desabrigados >= 0),
  desalojados integer check (desalojados is null or desalojados >= 0),
  outros_afetados integer check (outros_afetados is null or outros_afetados >= 0),
  danos_humanos_total integer check (danos_humanos_total is null or danos_humanos_total >= 0),
  danos_materiais_rs numeric(16, 2) check (danos_materiais_rs is null or danos_materiais_rs >= 0),
  prejuizo_publico_rs numeric(16, 2) check (prejuizo_publico_rs is null or prejuizo_publico_rs >= 0),
  prejuizo_privado_rs numeric(16, 2) check (prejuizo_privado_rs is null or prejuizo_privado_rs >= 0),
  chuva_relacionada boolean not null,
  versao_fonte varchar(200),
  consolidado_em date,
  coletado_em timestamptz not null,
  execucao_id uuid not null references app.etl_execucoes(id)
);
create index desastres_atlas_data on silver.desastres_atlas (data_evento desc);

create table gold.samu_demanda_semana (
  territorio_id varchar(80) not null references app.territorios(id),
  nivel varchar(10) not null check (nivel in ('bairro', 'distrito', 'municipio')),
  inicio date not null,
  grupo varchar(30) not null,
  chamados integer not null check (chamados > 0),
  incompleta boolean not null,
  dados_ate date not null,
  coletado_em timestamptz not null,
  primary key (territorio_id, inicio, grupo)
);
create index samu_demanda_gold_nivel on gold.samu_demanda_semana (nivel, inicio desc);

create table gold.agua_vigilancia_semana (
  territorio_id varchar(80) not null references app.territorios(id),
  nivel varchar(10) not null check (nivel in ('bairro', 'distrito', 'municipio')),
  inicio date not null,
  motivo_grupo varchar(10) not null,
  analises_ecoli integer not null,
  ecoli_presente integer not null,
  analises_cloro integer not null,
  cloro_fora_padrao integer not null,
  incompleta boolean not null,
  ultima_coleta date not null,
  ultimo_registro date not null,
  coletado_em timestamptz not null,
  primary key (territorio_id, inicio, motivo_grupo)
);
create index agua_vigilancia_gold_nivel on gold.agua_vigilancia_semana (nivel, inicio desc);

create table gold.desastres_historico (
  protocolo varchar(60) primary key,
  data_evento date not null,
  data_registro date,
  cobrade varchar(10),
  tipologia varchar(120),
  status varchar(30),
  mortos integer,
  feridos integer,
  desabrigados integer,
  desalojados integer,
  outros_afetados integer,
  danos_humanos_total integer,
  danos_materiais_rs numeric(16, 2),
  prejuizo_publico_rs numeric(16, 2),
  prejuizo_privado_rs numeric(16, 2),
  chuva_relacionada boolean not null,
  versao_fonte varchar(200),
  consolidado_em date,
  coletado_em timestamptz not null
);
create index desastres_historico_data on gold.desastres_historico (data_evento desc);
"""

FONTES = [
    # id, nome, órgão, url, tipo, licença, conector, limite_h, min_obs
    (
        "samu-recife",
        "Demanda de urgência (SAMU Recife): chamados por semana e bairro",
        "Prefeitura do Recife (Dados Abertos), Secretaria de Saúde",
        "https://dados.recife.pe.gov.br/dataset/servico-de-atendimento-movel-de-urgencia-samu-2026",
        "observada",
        "ODbL",
        "ConectorSamuRecife",
        1440,  # publicação mensal; 60 dias toleram uma publicação perdida
        1,
    ),
    (
        "sisagua",
        "Qualidade da água por bairro e semana (SISAGUA, vigilância)",
        "Ministério da Saúde — SISAGUA / API de Dados Abertos",
        "https://apidadosabertos.saude.gov.br/v1/",
        "observada",
        None,
        "ConectorSisagua",
        192,  # carga semanal mais um dia de folga
        1,
    ),
    (
        "atlas-desastres",
        "Histórico de desastres do Recife (Atlas Digital de Desastres no Brasil)",
        "Sedec/MIDR e Ceped/UFSC — Atlas Digital de Desastres no Brasil",
        "https://atlasdigital.mdr.gov.br/paginas/downloads.xhtml",
        "observada",
        None,
        "ConectorAtlasDesastres",
        13140,  # consolidação anual; 18 meses
        1,
    ),
]

GRANTS = f"""
do $$
begin
  if exists (select 1 from pg_roles where rolname = '{PAPEL}') then
    {"".join(f"execute 'grant select on silver.{t} to {PAPEL}'; " for t in SILVER)}
    {"".join(f"execute 'grant select on gold.{t} to {PAPEL}'; " for t in GOLD)}
    {"".join(f"execute 'revoke insert, update, delete, truncate on silver.{t} from {PAPEL}'; " for t in SILVER)}
    {"".join(f"execute 'revoke insert, update, delete, truncate on gold.{t} from {PAPEL}'; " for t in GOLD)}
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
                "licenca = excluded.licenca, conector = excluded.conector, "
                "limite_desatualizacao_h = excluded.limite_desatualizacao_h, "
                "min_observacoes = excluded.min_observacoes, implementada = true"
            ),
            dict(zip("abcdefghi", f, strict=True)),
        )
    op.execute(GRANTS)


def downgrade() -> None:
    op.execute(
        """
        drop table if exists gold.desastres_historico;
        drop table if exists gold.agua_vigilancia_semana;
        drop table if exists gold.samu_demanda_semana;
        drop table if exists silver.desastres_atlas;
        drop table if exists silver.agua_vigilancia_semana;
        drop table if exists silver.samu_demanda_semana;
        delete from app.fontes f where f.id in ('samu-recife', 'sisagua', 'atlas-desastres')
          and not exists (select 1 from app.etl_execucoes e where e.fonte_id = f.id);
        update app.fontes set implementada = false where id in ('samu-recife', 'sisagua', 'atlas-desastres');
        """
    )
