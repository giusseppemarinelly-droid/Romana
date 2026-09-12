"""pesaje manual + procedencia (comparación con manual de Bigsoft)

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-09-12 02:00:00.000000

A pedido tras comparar con el manual de Bigsoft (sistema anterior):

- es_manual: Bigsoft permite tipear el peso a mano cuando la báscula no
  responde (mantenimiento, corte de energía al adaptador, etc.),
  marcando el ticket como "manual" para trazabilidad. Simplificado a
  propósito: un solo flag por pesada (no un flag por cada una de las 3
  capturas, ni la regla de Bigsoft de "si empezó manual, debe terminar
  manual") -- solo importa poder saber después si algún peso de esta
  pesada no vino de la báscula.

- procedencia: el ticket ya tenía la etiqueta "Procedencia:" impresa
  (heredada del formato de Bigsoft) pero sin ningún campo detrás --
  quedaba siempre vacía.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('pesadas', sa.Column('es_manual', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('pesadas', sa.Column('procedencia', sa.String(length=150), nullable=True))


def downgrade() -> None:
    op.drop_column('pesadas', 'procedencia')
    op.drop_column('pesadas', 'es_manual')
