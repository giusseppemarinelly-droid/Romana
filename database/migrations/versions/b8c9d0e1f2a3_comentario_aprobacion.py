"""comentario de Centro de Costos al aprobar

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-09-24 15:00:00.000000

A pedido del usuario: al aprobar, Centro de Costos puede dejar por qué
aprobó (opcional). El rechazo ya tenía su motivo obligatorio
(motivo_rechazo). Lo usan igual la web de supervisión y la estación de
escritorio.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('pesadas', sa.Column('comentario_aprobacion', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('pesadas', 'comentario_aprobacion')
