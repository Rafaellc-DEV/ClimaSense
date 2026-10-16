"""Índice para os cenários: busca das emissões de previsão por fonte (T6.4).

Sem ele, montar o cenário de “Recife inteiro” varria toda a silver.observacoes (mais de 400 mil horas de
histórico) e levava dezenas de segundos.

Revisão: 0006
Anterior: 0005
"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "create index observacoes_emissao on silver.observacoes (fonte_id, emitido_em, territorio_id) "
        "where emitido_em is not null"
    )


def downgrade() -> None:
    op.execute("drop index if exists silver.observacoes_emissao")
