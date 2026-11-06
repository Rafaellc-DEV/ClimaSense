"""Faixa 70+ no lugar de 80+ em silver.populacao_bairro (RF-03, ADR 0010).

O IBGE não publica "80 anos ou mais" por bairro (só até "70 anos ou mais"); nada é estimado. Linhas `80+` não
existem (o conector nunca as gravou), mas são removidas por segurança antes de trocar o check.

Revisão: 0018
Anterior: 0017
"""

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None

CK = "populacao_bairro_faixa_check"


def _trocar(faixas: str) -> None:
    op.execute(f"alter table silver.populacao_bairro drop constraint if exists {CK}")
    op.execute(f"alter table silver.populacao_bairro add constraint {CK} check (faixa in ({faixas}))")


def upgrade() -> None:
    op.execute("delete from silver.populacao_bairro where faixa = '80+'")
    _trocar("'0-4', '0-14', '60+', '70+', 'total'")


def downgrade() -> None:
    op.execute("delete from silver.populacao_bairro where faixa = '70+'")
    _trocar("'0-4', '0-14', '60+', '80+', 'total'")
