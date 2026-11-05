"""Remove a funcionalidade de vacinação: o produto foca desastres naturais (chuva, alagamento, deslizamento).

O que sai:
- `gold.vacinacao_distrito_mes` (agregado por distrito e mês, servido em `/saude/vacinacao`, rota removida);
- a fonte `vacinacao` de `app.fontes` e as execuções de ETL dela em `app.etl_execucoes`.

O que fica, de propósito (legado do projeto antigo Projeto-ETL_AVD, decisão do usuário):
- `public.silver_vacinados_legado_etl_avd` (tabela renomeada pela 0002) e a view `public.silver_vacinados`;
- `silver.vacinados`, porque a view `public.silver_vacinados` lê dela. Ela perde só a chave estrangeira
  para `app.etl_execucoes` (as execuções da fonte removida deixam de existir); os dados ficam intactos.

`downgrade` recria a estrutura (tabela gold, fonte e chave estrangeira). As execuções apagadas e o conteúdo
da gold (derivado, recalculável pelo ETL antigo) não voltam; por isso a chave volta como `not valid`.

Revisão: 0009
Anterior: 0008
"""

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

UPGRADE = """
drop table if exists gold.vacinacao_distrito_mes;
alter table silver.vacinados drop constraint if exists vacinados_execucao_id_fkey;
delete from app.etl_execucoes where fonte_id = 'vacinacao';
delete from app.fontes where id = 'vacinacao';
"""

DOWNGRADE = """
insert into app.fontes (id, nome, orgao, url, tipo, licenca, conector, limite_desatualizacao_h, min_observacoes,
                        implementada)
values ('vacinacao', 'Perfil das pessoas vacinadas — COVID-19', 'Prefeitura do Recife (Dados Abertos)',
        'https://dados.recife.pe.gov.br/dataset/perfil-das-pessoas-vacinadas-covid-19', 'observada', 'ODbL',
        'ConectorVacinacao', 744, 30, true)
on conflict (id) do nothing;

alter table silver.vacinados
  add constraint vacinados_execucao_id_fkey foreign key (execucao_id) references app.etl_execucoes(id) not valid;

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
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
