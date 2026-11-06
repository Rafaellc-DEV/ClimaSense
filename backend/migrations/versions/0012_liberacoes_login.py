"""Desbloqueio de login pelo administrador (RNF-01, T0.4).

- app.liberacoes_login: cada linha diz "ignore as falhas de login deste e-mail e/ou deste IP anteriores a `em`".
  Só se inclui; nada é apagado nem alterado (a ação também vai para a auditoria).
- índice em app.tentativas_login (ip, em) para o limite por IP.

Revisão: 0012
Anterior: 0011
"""

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        create table app.liberacoes_login (
          id bigserial primary key,
          email varchar(254),
          ip inet,
          em timestamptz not null,
          admin_id uuid not null references app.usuarios(id),
          check (email is not null or ip is not null)
        );
        create index liberacoes_login_email_em on app.liberacoes_login (email, em desc);
        create index liberacoes_login_ip_em on app.liberacoes_login (ip, em desc);
        create index tentativas_login_ip_em on app.tentativas_login (ip, em desc);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        drop index if exists app.tentativas_login_ip_em;
        drop table if exists app.liberacoes_login;
        """
    )
