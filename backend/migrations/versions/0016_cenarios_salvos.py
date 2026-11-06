"""Cenários salvos do simulador (RF-27, RN-11).

Guarda as premissas, o resultado calculado pelo servidor, o autor e a hora. Somente-inclusão (gatilhos de
`somente_inclusao_evento`): o cenário salvo é registro do que se viu naquele momento e entra no relatório. O papel
`climasense_app` só tem SELECT e INSERT (ADR 0014); UPDATE, DELETE e TRUNCATE são revogados de forma explícita.
Só dados agregados por território, nunca registro individual (RN-13).

Revisão: 0016
Anterior: 0015
"""

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None

PAPEL = "climasense_app"

SQL = """
create table app.cenarios (
  id uuid primary key default gen_random_uuid(),
  nome varchar(120) not null check (length(btrim(nome)) > 0),
  premissas jsonb not null,
  resultado jsonb not null,
  autor_id uuid not null references app.usuarios(id),
  criado_em timestamptz not null default now()
);
create index cenarios_recentes on app.cenarios (criado_em desc);

create trigger cenarios_somente_inclusao before update or delete on app.cenarios
  for each row execute function app.somente_inclusao_evento();
create trigger cenarios_sem_truncate before truncate on app.cenarios
  for each statement execute function app.somente_inclusao_evento();
"""

GRANTS = f"""
do $$
begin
  if exists (select 1 from pg_roles where rolname = '{PAPEL}') then
    execute 'grant select, insert on app.cenarios to {PAPEL}';
    execute 'revoke update, delete, truncate on app.cenarios from {PAPEL}';
  end if;
end $$;
"""


def upgrade() -> None:
    op.execute(SQL)
    op.execute(GRANTS)


def downgrade() -> None:
    op.execute("drop table if exists app.cenarios")
