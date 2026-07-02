# ============================================================
# database/migrate.py — Migración segura de la base de datos
# ============================================================
# Este script agrega las nuevas columnas a la BD existente
# SIN borrar datos anteriores. Se ejecuta automáticamente
# al iniciar la aplicación.

from database.engine import engine
import sqlalchemy as sa


def _column_exists(conn, table: str, column: str) -> bool:
    """Verifica si una columna ya existe en una tabla (SQLite)."""
    result = conn.execute(sa.text(f"PRAGMA table_info({table})"))
    cols = [row[1] for row in result.fetchall()]
    return column in cols


def _add_column_if_missing(conn, table: str, column: str, definition: str):
    """Agrega una columna solo si no existe."""
    if not _column_exists(conn, table, column):
        conn.execute(sa.text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))
        print(f"  Agregada columna: {table}.{column}")


def ejecutar_migracion():
    """
    Agrega todas las columnas nuevas del flujo Romana/Centro de Costos.
    Seguro de ejecutar múltiples veces (idempotente).
    """
    print("Verificando esquema de base de datos...")

    with engine.connect() as conn:
        # ── Tabla: pesadas ──────────────────────────────────────
        _add_column_if_missing(conn, "pesadas", "tipo_pesaje",
                               "VARCHAR(30) DEFAULT 'GENERAL'")
        _add_column_if_missing(conn, "pesadas", "empresa_transportista",
                               "VARCHAR(150)")
        _add_column_if_missing(conn, "pesadas", "empresa_cliente_proveedor",
                               "VARCHAR(150)")
        _add_column_if_missing(conn, "pesadas", "cedula_conductor_libre",
                               "VARCHAR(30)")
        _add_column_if_missing(conn, "pesadas", "orden_compra",
                               "VARCHAR(100)")
        _add_column_if_missing(conn, "pesadas", "cantidad",
                               "NUMERIC(10,2)")
        _add_column_if_missing(conn, "pesadas", "precintos",
                               "VARCHAR(200)")
        _add_column_if_missing(conn, "pesadas", "fecha_captura",
                               "DATETIME")
        _add_column_if_missing(conn, "pesadas", "aprobado_por_id",
                               "INTEGER REFERENCES usuarios(id)")
        _add_column_if_missing(conn, "pesadas", "fecha_aprobacion",
                               "DATETIME")
        _add_column_if_missing(conn, "pesadas", "motivo_rechazo",
                               "TEXT")

        # Migrar estados antiguos al nuevo esquema
        conn.execute(sa.text(
            "UPDATE pesadas SET estado='en_planta' WHERE estado='pendiente'"
        ))
        conn.execute(sa.text(
            "UPDATE pesadas SET estado='completado' WHERE estado='completada'"
        ))
        conn.execute(sa.text(
            "UPDATE pesadas SET estado='anulado' WHERE estado='anulada'"
        ))

        # ── Tabla: productos ────────────────────────────────────
        _add_column_if_missing(conn, "productos", "tipo_pesaje",
                               "VARCHAR(30) DEFAULT 'GENERAL'")

        conn.commit()

    print("OK - Esquema de base de datos actualizado")



if __name__ == "__main__":
    ejecutar_migracion()
