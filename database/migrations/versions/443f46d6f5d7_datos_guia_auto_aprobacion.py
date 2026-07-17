"""datos de guía (código viaje, peso guía, bultos) + auto_aprobado

Revision ID: 443f46d6f5d7
Revises: d4e5f6a7b8c9
Create Date: 2026-07-17 00:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '443f46d6f5d7'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('pesadas', sa.Column('codigo_viaje', sa.String(length=50), nullable=True))
    op.add_column('pesadas', sa.Column('peso_guia', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('pesadas', sa.Column('bultos', sa.Integer(), nullable=True))
    op.add_column(
        'pesadas',
        sa.Column('auto_aprobado', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column('pesadas', 'auto_aprobado')
    op.drop_column('pesadas', 'bultos')
    op.drop_column('pesadas', 'peso_guia')
    op.drop_column('pesadas', 'codigo_viaje')
