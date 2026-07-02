"""indices de busqueda trigram (placa, documento, nombre)

Revision ID: a1b2c3d4e5f6
Revises: 86678fdd4d8a
Create Date: 2026-07-02 14:20:00.000000

Resuelve el cuello de botella #1 de Bigsoft: búsqueda de
conductores/vehículos por Cédula/Placa. `pg_trgm` permite que un
`ILIKE '%texto%'` (contiene, no solo empieza-con) use un índice en vez
de un full scan — necesario porque el operador busca por fragmentos
parciales de placa o documento, no por prefijo exacto.

Específico de PostgreSQL: no se aplica sobre SQLite (usado solo para
generar la migración baseline en desarrollo local sin Postgres a mano).
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "86678fdd4d8a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE INDEX IF NOT EXISTS ix_vehiculos_placa_trgm ON vehiculos USING gin (placa gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_conductores_documento_trgm ON conductores USING gin (documento gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_conductores_nombre_trgm ON conductores USING gin (nombre gin_trgm_ops)")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("DROP INDEX IF EXISTS ix_conductores_nombre_trgm")
    op.execute("DROP INDEX IF EXISTS ix_conductores_documento_trgm")
    op.execute("DROP INDEX IF EXISTS ix_vehiculos_placa_trgm")
