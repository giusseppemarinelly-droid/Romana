# ============================================================
# backend/tests/conftest.py
# ============================================================
# Usa un SQLite de archivo (no Postgres) para que la suite corra sin
# depender de un servidor externo instalado. La lógica bajo prueba es
# la máquina de estados de negocio (services/pesaje_service.py), que
# no usa ninguna característica exclusiva de Postgres — ILIKE, por
# ejemplo, se traduce igual en ambos dialectos. Las migraciones que sí
# son Postgres-only (pg_trgm) se auto-excluyen en SQLite (ver
# database/migrations/versions/*_trgm.py).
#
# IMPORTANTE: las variables de entorno se fijan a nivel de módulo,
# ANTES de cualquier import de database/services/backend — pytest
# importa conftest.py antes de recolectar los tests, así que
# `database.engine` crea su engine ya apuntando al SQLite de prueba.
import os
from pathlib import Path

_TEST_DB_PATH = Path(__file__).resolve().parent / "_test_romana.db"
_TEST_DB_PATH.unlink(missing_ok=True)
os.environ["ROMANA_DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"
os.environ["ROMANA_JWT_SECRET"] = "test-secret-no-usar-en-produccion"

import bcrypt
import pytest
from fastapi.testclient import TestClient

from database import models
from database.engine import Base, SessionLocal, engine
from backend.main import app

Base.metadata.create_all(bind=engine)


def _crear_usuario(db, username, nivel):
    usuario = models.Usuario(
        username=username,
        password_hash=bcrypt.hashpw(b"clave123", bcrypt.gensalt()).decode("utf-8"),
        nombre_completo=f"Usuario prueba {username}",
        nivel=nivel,
        activo=True,
    )
    db.add(usuario)
    return usuario


@pytest.fixture(scope="session", autouse=True)
def _seed():
    db = SessionLocal()
    try:
        _crear_usuario(db, "admin_test", 1)
        _crear_usuario(db, "romana_test", 3)
        _crear_usuario(db, "cc_test", 4)
        vehiculo = models.Vehiculo(placa="TEST-001", descripcion="Camión de prueba", activo=True)
        vehiculo_b = models.Vehiculo(placa="TEST-002", descripcion="Camión de prueba B", activo=True)
        db.add_all([vehiculo, vehiculo_b])
        db.commit()
    finally:
        db.close()


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def _login(client, username) -> str:
    r = client.post("/api/v1/auth/login", json={"username": username, "password": "clave123"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def token_admin(client):
    return _login(client, "admin_test")


@pytest.fixture(scope="session")
def headers_admin(token_admin):
    return {"Authorization": f"Bearer {token_admin}"}


@pytest.fixture(scope="session")
def token_romana(client):
    return _login(client, "romana_test")


@pytest.fixture(scope="session")
def token_cc(client):
    return _login(client, "cc_test")


@pytest.fixture(scope="session")
def headers_romana(token_romana):
    return {"Authorization": f"Bearer {token_romana}"}


@pytest.fixture(scope="session")
def headers_cc(token_cc):
    return {"Authorization": f"Bearer {token_cc}"}


@pytest.fixture(scope="session")
def vehiculo_id(client, headers_romana):
    r = client.get("/api/v1/vehiculos", params={"search": "TEST-001"}, headers=headers_romana)
    assert r.status_code == 200, r.text
    return r.json()[0]["id"]


@pytest.fixture(scope="session")
def vehiculo_b_id(client, headers_romana):
    r = client.get("/api/v1/vehiculos", params={"search": "TEST-002"}, headers=headers_romana)
    assert r.status_code == 200, r.text
    return r.json()[0]["id"]
