# ============================================================
# database/engine.py — Conexión a la base de datos
# ============================================================
# SQLAlchemy es la librería que nos permite hablar con la base
# de datos usando Python puro, sin escribir SQL directamente.
#
# ¿Qué es SQLite?
#   SQLite guarda TODA la base de datos en UN SOLO ARCHIVO
#   (romana.db). No necesita instalar ningún servidor de base
#   de datos. Perfecto para sistemas de escritorio en Windows.

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import DATABASE_URL

# -------------------------------------------------------
# Clase base para todos los modelos de la base de datos.
# Todos los modelos (tablas) heredan de esta clase.
# -------------------------------------------------------
class Base(DeclarativeBase):
    pass

# -------------------------------------------------------
# Motor de base de datos
# echo=False: no imprime SQL en consola (ponlo True para debug)
# -------------------------------------------------------
engine = create_engine(DATABASE_URL, echo=False)

# -------------------------------------------------------
# Fábrica de sesiones.
# Una "sesión" es una unidad de trabajo con la base de datos.
# Siempre trabajamos con sesiones para leer/escribir datos.
# -------------------------------------------------------
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Los objetos conservan sus datos despues del commit/close
)

def get_db():
    """
    Función generadora que crea y cierra sesiones de BD.
    Uso:
        db = next(get_db())
        # ... trabajar con db ...
        db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def crear_tablas():
    """
    Crea todas las tablas en la base de datos si no existen.
    Se llama una sola vez al iniciar el sistema.
    """
    # Importamos los modelos para que SQLAlchemy los registre
    from database import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    print("OK - Base de datos lista")

