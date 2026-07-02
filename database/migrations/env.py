# ============================================================
# database/migrations/env.py — Configuración de Alembic
# ============================================================
# Reemplaza a database/migrate.py (script manual con sintaxis SQLite
# que no funcionaba contra el Postgres real de config.py).
#
# La BD real ya tiene las tablas creadas por database/seed.py en
# despliegues existentes. Para esos casos, la primera migración se
# aplica con `alembic stamp head` (marca el baseline sin ejecutar
# CREATE TABLE) en vez de `alembic upgrade head`. Instalaciones nuevas
# sí corren `alembic upgrade head` normalmente.

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from config import DATABASE_URL
from database.engine import Base
from database import models  # noqa: F401 — registra los modelos en Base.metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", DATABASE_URL)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
