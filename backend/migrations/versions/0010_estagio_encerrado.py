"""Permite ENCERRAR um estágio declarado.

Antes, uma declaração (ex.: “Crítico”) só podia ser substituída por outra declaração: não havia como dizer
“acabou”. A tabela de declarações é somente de inclusão (RN-03: nada é alterado nem apagado), então encerrar é
uma NOVA linha com o estágio `encerrado`. O serviço trata a mais recente `encerrado` como “sem declaração”
(o território volta a mostrar só o estágio sugerido) e o histórico guarda quem encerrou, quando e por quê.

Revisão: 0010
Anterior: 0009
"""

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter table app.estagio_declaracoes drop constraint estagio_declaracoes_estagio_check")
    op.execute(
        "alter table app.estagio_declaracoes add constraint estagio_declaracoes_estagio_check "
        "check (estagio in ('observacao','atencao','alerta','critico','encerrado'))"
    )


def downgrade() -> None:
    # `not valid`: linhas `encerrado` já gravadas continuam (o histórico é imutável); só novas linhas são checadas
    op.execute("alter table app.estagio_declaracoes drop constraint estagio_declaracoes_estagio_check")
    op.execute(
        "alter table app.estagio_declaracoes add constraint estagio_declaracoes_estagio_check "
        "check (estagio in ('observacao','atencao','alerta','critico')) not valid"
    )
