"""peso_entrada: separa el 1er pesaje del bruto/tara recalculados

Antes de esta columna, `peso_bruto` cumplía dos funciones incompatibles:
guardaba el peso de entrada al registrar el camión, y se sobrescribía con el
mayor de los dos pesajes al capturar la salida. El peso de entrada quedaba
irrecuperable, y una re-captura tras un rechazo de Centro de Costos calculaba
el neto contra el bruto de la captura anterior en vez de contra la entrada.

BACKFILL -- solo se rellena lo que se puede saber con certeza:

  * `en_planta`: nunca hubo captura, así que `peso_bruto` sigue siendo el peso
    de entrada tal cual se registró. Se copia.

  * Cualquier otro estado: ya hubo al menos una captura, y `peso_bruto`/
    `peso_tara` quedaron como mayor/menor de los dos pesajes sin registro de
    cuál de los dos fue la entrada. El dato es genuinamente irrecuperable, así
    que la columna queda en NULL en vez de inventar un valor plausible.
    `capturar_peso_salida()` se niega a re-capturar una fila con
    `peso_entrada` NULL y explica por qué -- las pesadas ya completadas no se
    ven afectadas, porque su neto ya está calculado y cerrado.

Revision ID: e5f6a7b8c9d0
Revises: 443f46d6f5d7
Create Date: 2026-09-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = '443f46d6f5d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('pesadas', sa.Column('peso_entrada', sa.Numeric(precision=10, scale=2), nullable=True))
    op.execute(
        "UPDATE pesadas SET peso_entrada = peso_bruto "
        "WHERE estado = 'en_planta' AND peso_bruto IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column('pesadas', 'peso_entrada')
