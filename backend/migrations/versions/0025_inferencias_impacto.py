"""RF-19, RF-27, RF-42: inferências acumulativas na silver e view gold reproduzível.

Só a rotina explícita de inferência persiste. GET não grava. Sem cenário manual e sem
experimento reprovado na tabela operacional. Migrações anteriores permanecem intactas.
"""

from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None

SQL = """
create table silver.inferencias_impacto (
  id bigserial primary key,
  territorio_id varchar(80) not null references app.territorios(id),
  distrito_id varchar(80) not null references app.territorios(id),
  tipo_impacto varchar(20) not null check (tipo_impacto in ('alagamento', 'deslizamento')),
  metodo varchar(80) not null,
  versao_modelo varchar(30) not null,
  classe_resultado varchar(20) not null check (classe_resultado in
    ('sem_dados', 'observacao', 'atencao', 'alerta', 'critico', 'baixo', 'moderado', 'alto')),
  confianca_qualitativa varchar(15) not null check (confianca_qualitativa in ('baixa', 'media', 'insuficiente')),
  status_validacao varchar(30) not null check (status_validacao in ('regra_experimental', 'ml_temporal')),
  data_previsao timestamptz not null,
  emitido_em_fonte timestamptz,
  inicio_validade timestamptz not null,
  fim_validade timestamptz not null check (fim_validade > inicio_validade),
  horizonte_h integer not null check (horizonte_h between 1 and 72),
  fonte_meteorologica varchar(80) not null references app.fontes(id),
  fatores jsonb not null,
  insumos jsonb not null,
  motivo_indisponibilidade text,
  hash_entrada char(64) not null unique,
  criado_em timestamptz not null default now(),
  check (status_validacao <> 'ml_temporal' or tipo_impacto = 'alagamento')
);
create index inferencias_impacto_territorio_data on silver.inferencias_impacto (territorio_id, data_previsao desc);
create view gold.previsoes_impacto as select * from silver.inferencias_impacto;
create trigger inferencias_impacto_somente_inclusao before update or delete on silver.inferencias_impacto
  for each row execute function app.somente_inclusao_evento();
create trigger inferencias_impacto_sem_truncate before truncate on silver.inferencias_impacto
  for each statement execute function app.somente_inclusao_evento();
do $$ begin
  if exists (select 1 from pg_roles where rolname = 'climasense_app') then
    grant select, insert on silver.inferencias_impacto to climasense_app;
    grant usage, select on sequence silver.inferencias_impacto_id_seq to climasense_app;
    grant select on gold.previsoes_impacto to climasense_app;
    revoke update, delete, truncate on silver.inferencias_impacto from climasense_app;
  end if;
end $$;
"""


def upgrade() -> None:
    op.execute(SQL)


def downgrade() -> None:
    op.execute("drop view gold.previsoes_impacto; drop table silver.inferencias_impacto")
