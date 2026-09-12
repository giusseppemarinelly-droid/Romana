# ============================================================
# test_auth_endpoints.py — C-02: endpoints que respondían sin token
# ============================================================
# Hallazgo de la auditoría (commit c97fdcc): seis GET de listados/kardex
# en backend/routers/pesadas.py no declaraban ninguna dependencia de
# autenticación -- cualquier máquina de la red podía leerlos sin
# credenciales. Este test fija el contrato: todos deben exigir un
# Bearer token válido, y responder con datos una vez autenticados.

import pytest

from database.engine import SessionLocal
from database.models import Vehiculo
from services import pesaje_service

ENDPOINTS_GET = [
    "/api/v1/pesadas/en-planta",
    "/api/v1/pesadas/aprobadas-pendientes",
    "/api/v1/pesadas/completadas",
    "/api/v1/pesadas/estadisticas",
    "/api/v1/pesadas/kardex/buscar",
]


@pytest.mark.parametrize("path", ENDPOINTS_GET)
def test_endpoint_rechaza_sin_token(client, path):
    r = client.get(path)
    assert r.status_code == 401, f"{path} respondió {r.status_code} sin token (esperado 401)"


@pytest.mark.parametrize("path", ENDPOINTS_GET)
def test_endpoint_acepta_token_romana(client, headers_romana, path):
    r = client.get(path, headers=headers_romana)
    assert r.status_code == 200, r.text


def test_pesada_por_id_rechaza_sin_token(client, headers_romana):
    # Vehículo dedicado (no el de los fixtures compartidos) para no chocar
    # con el índice único de pesada activa si otro test corre en paralelo
    # o en otro orden -- mismo patrón que test_concurrencia_* en
    # test_flujo_pesaje.py.
    db = SessionLocal()
    try:
        vehiculo = Vehiculo(placa="TEST-AUTH-001", descripcion="Solo para este test", activo=True)
        db.add(vehiculo)
        db.commit()
        db.refresh(vehiculo)
        vehiculo_id = vehiculo.id
    finally:
        db.close()

    resultado = pesaje_service.registrar_entrada(
        peso_bruto=15000, vehiculo_id=vehiculo_id, tipo_pesaje="GENERAL"
    )
    assert resultado["exito"], resultado["mensaje"]
    pesada_id = resultado["pesada"].id

    r = client.get(f"/api/v1/pesadas/{pesada_id}")
    assert r.status_code == 401

    r = client.get(f"/api/v1/pesadas/{pesada_id}", headers=headers_romana)
    assert r.status_code == 200

    r = client.get(f"/api/v1/pesadas/vehiculo/{vehiculo_id}/activa")
    assert r.status_code == 401


def test_kardex_rechaza_nivel_centro_costos(client, headers_cc):
    # El sidebar de la GUI ya oculta "Kardex" a Centro de Costos (nivel 4,
    # permiso reportes_ver = [1,2,3]) -- el backend debe exigir lo mismo.
    r = client.get("/api/v1/pesadas/kardex/buscar", headers=headers_cc)
    assert r.status_code == 403
