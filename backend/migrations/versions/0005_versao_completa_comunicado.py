"""Versões de comunicado completas: território, público, nível e validade também ficam na versão (T7.3).

Sem isso, mudar o nível ou a validade de um comunicado aprovado mudaria o que vai para a landing sem nova
revisão. Agora a versão é a fotografia inteira do que foi revisado, e o hash cobre tudo (RN-03, RN-04).

Revisão: 0005
Anterior: 0004
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        alter table app.comunicado_versoes
          add column territorios varchar(80)[] not null default '{}',
          add column publico varchar(40) not null default 'populacao',
          add column nivel varchar(15) not null default 'informativo'
            check (nivel in ('informativo','atencao','alerta','critico')),
          add column validade_inicio timestamptz,
          add column validade_fim timestamptz;
        alter table app.comunicado_versoes alter column territorios drop default,
          alter column publico drop default, alter column nivel drop default;
        alter table app.comunicados add column criado_por uuid references app.usuarios(id),
          add column criado_em timestamptz not null default now(),
          add column atualizado_em timestamptz not null default now();
        alter table app.avaliacoes add column atualizado_em timestamptz not null default now();
        create index comunicado_versoes_comunicado on app.comunicado_versoes (comunicado_id, numero);
        create index avaliacao_versoes_avaliacao on app.avaliacao_versoes (avaliacao_id, numero);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        drop index if exists app.avaliacao_versoes_avaliacao;
        drop index if exists app.comunicado_versoes_comunicado;
        alter table app.avaliacoes drop column atualizado_em;
        alter table app.comunicados drop column atualizado_em, drop column criado_em, drop column criado_por;
        alter table app.comunicado_versoes drop column validade_fim, drop column validade_inicio,
          drop column nivel, drop column publico, drop column territorios;
        """
    )
