"""Estágio oficial da cidade dado pelo COP (RF-01, RN-01, RN-05).

Registro manual da equipe enquanto não houver feed do COP. Histórico somente-inclusão (gatilhos de
`somente_inclusao_evento`, como as declarações da 0007). O papel `climasense_app` só tem SELECT e INSERT
(ADR 0014): UPDATE, DELETE e TRUNCATE são revogados de forma explícita.

Revisão: 0015
Anterior: 0014
"""

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

PAPEL = "climasense_app"

SQL = """
create table app.estagio_oficial (
  id uuid primary key default gen_random_uuid(),
  estagio varchar(12) not null check (estagio in ('observacao','atencao','alerta','critico')),
  informado_em timestamptz not null,
  observacao varchar(500),
  autor_id uuid not null references app.usuarios(id),
  registrado_em timestamptz not null default now()
);
create index estagio_oficial_vigente on app.estagio_oficial (informado_em desc, registrado_em desc);

create trigger estagio_oficial_somente_inclusao before update or delete on app.estagio_oficial
  for each row execute function app.somente_inclusao_evento();
create trigger estagio_oficial_sem_truncate before truncate on app.estagio_oficial
  for each statement execute function app.somente_inclusao_evento();
"""

GRANTS = f"""
do $$
begin
  if exists (select 1 from pg_roles where rolname = '{PAPEL}') then
    execute 'grant select, insert on app.estagio_oficial to {PAPEL}';
    execute 'revoke update, delete, truncate on app.estagio_oficial from {PAPEL}';
  end if;
end $$;
"""


def upgrade() -> None:
    op.execute(SQL)
    op.execute(GRANTS)


def downgrade() -> None:
    op.execute("drop table if exists app.estagio_oficial")
