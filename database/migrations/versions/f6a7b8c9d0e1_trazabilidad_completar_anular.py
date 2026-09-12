"""trazabilidad de completar y anular (I-05, I-06)

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-12 01:00:00.000000

I-05: anular_pesada() no recibía usuario_id -- la anulación, la
operación más sensible del sistema después del cierre, era la única
transición de estado sin constancia de quién la hizo.

I-06: completar_pesaje() reescribía usuario_salida_id con el usuario
que completó el pesaje, perdiendo quién había capturado el 2° peso si
fueron operadores de turnos distintos.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('pesadas', sa.Column('usuario_completado_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True))
    op.add_column('pesadas', sa.Column('anulado_por_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True))
    op.add_column('pesadas', sa.Column('fecha_anulacion', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('pesadas', 'fecha_anulacion')
    op.drop_column('pesadas', 'anulado_por_id')
    op.drop_column('pesadas', 'usuario_completado_id')
