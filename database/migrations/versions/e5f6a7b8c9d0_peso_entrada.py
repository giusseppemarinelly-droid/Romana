"""peso entrada (C-01: separa el peso de entrada de peso_bruto)

Revision ID: e5f6a7b8c9d0
Revises: 443f46d6f5d7
Create Date: 2026-09-12 00:00:00.000000

Hallazgo C-01 de la auditoría (commit c97fdcc), reproducido en pruebas
de campo: peso_bruto cumplía dos funciones incompatibles -- guardaba el
peso de entrada al registrar la entrada, y se sobrescribía en cada
captura de salida (incluida una re-captura tras un rechazo de Centro de
Costos). El peso de entrada original no se conservaba en ningún otro
lado: se perdía de forma irrecuperable en la primera captura, y el
peso neto quedaba mal calculado si hubo un rechazo de por medio.

Backfill best-effort para filas ya existentes: no hay forma de saber,
después del hecho, si una fila completada pasó por un ciclo de rechazo
(rechazar_pesada() limpia motivo_rechazo en la re-captura, así que esa
señal tampoco sobrevive). Se asume el caso común -- sin rechazo -- y se
recupera peso_entrada como el menor de (peso_bruto, peso_tara) si ambos
existen (equivalente a asumir "camión entra vacío, sale cargado"), o
como peso_bruto si la pesada quedó en "en_planta" (todavía no hay 2°
captura, peso_bruto sigue siendo el de entrada). Las filas que sí
tuvieron un rechazo de por medio quedan con un peso_entrada backfillado
incorrecto -- inevitable sin el dato original -- pero es una situación
solo de datos históricos, no del código hacia adelante.
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

    pesadas = sa.table(
        'pesadas',
        sa.column('id', sa.Integer),
        sa.column('estado', sa.String),
        sa.column('peso_bruto', sa.Numeric),
        sa.column('peso_tara', sa.Numeric),
        sa.column('peso_entrada', sa.Numeric),
    )

    # Todavía en "en_planta": no hubo 2° captura, peso_bruto es la entrada.
    op.execute(
        pesadas.update()
        .where(pesadas.c.estado == 'en_planta')
        .values(peso_entrada=pesadas.c.peso_bruto)
    )

    # Ya pasó por capturar_peso_salida (cualquier otro estado con ambos
    # pesos presentes): best-effort, ver docstring del módulo. CASE en vez
    # de func.least() -- least() no existe en SQLite (usado en los tests),
    # CASE sí es portable entre Postgres y SQLite.
    menor = sa.case(
        (pesadas.c.peso_bruto < pesadas.c.peso_tara, pesadas.c.peso_bruto),
        else_=pesadas.c.peso_tara,
    )
    op.execute(
        pesadas.update()
        .where(pesadas.c.estado != 'en_planta')
        .where(pesadas.c.peso_bruto.isnot(None))
        .where(pesadas.c.peso_tara.isnot(None))
        .values(peso_entrada=menor)
    )


def downgrade() -> None:
    op.drop_column('pesadas', 'peso_entrada')
