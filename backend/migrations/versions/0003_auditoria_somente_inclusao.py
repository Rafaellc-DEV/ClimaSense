"""Auditoria somente-inclusão (T2.6, RF-14.2).

Triggers barram UPDATE, DELETE e TRUNCATE para qualquer papel, inclusive o dono da tabela
(no Neon a aplicação costuma conectar como dono, então só revogar privilégios não bastaria).

Revisão: 0003
Anterior: 0002
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

SQL = """
create function app.auditoria_imutavel() returns trigger language plpgsql as $$
begin
  raise exception 'A auditoria aceita apenas inclusões (RF-14.2).' using errcode = 'insufficient_privilege';
end $$;
create trigger auditoria_sem_alteracao before update or delete on app.auditoria
  for each row execute function app.auditoria_imutavel();
create trigger auditoria_sem_truncate before truncate on app.auditoria
  for each statement execute function app.auditoria_imutavel();
"""


def upgrade() -> None:
    op.execute(SQL)


def downgrade() -> None:
    op.execute(
        "drop trigger if exists auditoria_sem_truncate on app.auditoria;"
        "drop trigger if exists auditoria_sem_alteracao on app.auditoria;"
        "drop function if exists app.auditoria_imutavel();"
    )
