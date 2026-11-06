"""Apaga do banco os dados individuais de vacinação (RNF-03, RNF-12, ADR 0010 decisão 7).

Sai: a view `public.silver_vacinados`, as tabelas `silver.vacinados`, `public.silver_vacinados_legado_etl_avd` e
`public.gold_previsoes` (legado do ETL antigo). A exportação cifrada e validada foi feita antes, fora do repositório.
Sem CASCADE de propósito: se algo ainda depender dessas tabelas, a migração falha em vez de apagar mais.

`downgrade` NÃO traz dados de volta: recria só `silver.vacinados` (vazia) e a view, para que a cadeia de downgrades
(0009, 0002) continue funcionando. As outras duas tabelas eram do ETL antigo e não têm estrutura no repositório.

Revisão: 0013
Anterior: 0012
"""

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

UPGRADE = """
drop view if exists public.silver_vacinados;
drop table if exists silver.vacinados;
drop table if exists public.silver_vacinados_legado_etl_avd;
drop table if exists public.gold_previsoes;
"""

DOWNGRADE = """
create table if not exists silver.vacinados (
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
  execucao_id uuid not null
);
create or replace view public.silver_vacinados as
  select faixa_etaria, idade, sexo, raca_cor, municipio, grupo, categoria, lote, vacina, dose,
         data_vacinacao, distrito_sanitario, unidade_saude, sistema_origem
  from silver.vacinados;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
