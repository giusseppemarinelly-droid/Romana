"""indice unico parcial: una sola pesada activa por vehiculo

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-02 14:30:00.000000

services/pesaje_service.registrar_entrada() ya validaba "el vehículo no
puede tener 2 pesadas activas" a nivel de aplicación (SELECT, luego
INSERT si no hay ninguna) — pero eso es un check-then-act: bajo
concurrencia real (dos operadores/requests simultáneos para el mismo
vehículo) ambos pueden pasar la validación antes de que cualquiera
haga commit, resultando en dos pesadas activas para el mismo camión.

Este índice único parcial hace que la propia base de datos rechace esa
segunda fila, cerrando la condición de carrera sin necesitar locks
explícitos. El chequeo en pesaje_service.py se mantiene (da un mensaje
de error amigable en el caso común, no concurrente); el índice es la
red de seguridad real para el caso concurrente.

Soportado tanto en PostgreSQL como en SQLite (índices parciales con
WHERE) — no requiere ninguna extensión.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ESTADOS_ACTIVOS = "('en_planta','pendiente_aprobacion','aprobado','rechazado')"


def upgrade() -> None:
    op.execute(
        f"CREATE UNIQUE INDEX ux_pesada_activa_por_vehiculo ON pesadas (vehiculo_id) "
        f"WHERE estado IN {ESTADOS_ACTIVOS} AND anulada = false"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_pesada_activa_por_vehiculo")
