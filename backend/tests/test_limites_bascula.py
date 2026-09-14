# ============================================================
# test_limites_bascula.py — I-03: valida contra config.BASCULA
# ============================================================
# Antes, cada captura validaba el mínimo contra un 200 escrito a mano
# en el código, y nada validaba el techo -- una trama corrupta que
# parseara a un peso absurdo entraba al sistema igual.

from config import BASCULA
from database.engine import SessionLocal
from database.models import Vehiculo


def _vehiculo_dedicado(placa: str) -> int:
    db = SessionLocal()
    try:
        v = Vehiculo(placa=placa, descripcion="Solo para este test", activo=True)
        db.add(v)
        db.commit()
        db.refresh(v)
        return v.id
    finally:
        db.close()


def test_entrada_rechaza_peso_bajo_el_minimo_configurado(client, headers_romana):
    vehiculo_id = _vehiculo_dedicado("TEST-LIMITE-001")
    r = client.post(
        "/api/v1/pesadas/entrada",
        json={
            "peso_bruto": BASCULA["capacidad_min"] - 1,
            "vehiculo_id": vehiculo_id, "tipo_pesaje": "GENERAL",
        },
        headers=headers_romana,
    )
    assert r.status_code == 400
    assert "báscula" in r.json()["detail"].lower() or "bajo" in r.json()["detail"].lower()


def test_entrada_rechaza_peso_sobre_la_capacidad_maxima(client, headers_romana):
    vehiculo_id = _vehiculo_dedicado("TEST-LIMITE-002")
    r = client.post(
        "/api/v1/pesadas/entrada",
        json={
            "peso_bruto": BASCULA["capacidad_max"] + 1,
            "vehiculo_id": vehiculo_id, "tipo_pesaje": "GENERAL",
        },
        headers=headers_romana,
    )
    assert r.status_code == 400
    assert "capacidad" in r.json()["detail"].lower()


def test_entrada_acepta_peso_dentro_del_rango(client, headers_romana):
    vehiculo_id = _vehiculo_dedicado("TEST-LIMITE-003")
    r = client.post(
        "/api/v1/pesadas/entrada",
        json={
            "peso_bruto": BASCULA["capacidad_max"],  # justo en el borde -- debe aceptarse
            "vehiculo_id": vehiculo_id, "tipo_pesaje": "GENERAL",
        },
        headers=headers_romana,
    )
    assert r.status_code == 200, r.text


def test_salida_rechaza_peso_sobre_la_capacidad_maxima(client, headers_romana):
    vehiculo_id = _vehiculo_dedicado("TEST-LIMITE-004")
    r = client.post(
        "/api/v1/pesadas/entrada",
        json={"peso_bruto": 15000, "vehiculo_id": vehiculo_id, "tipo_pesaje": "GENERAL"},
        headers=headers_romana,
    )
    pesada_id = r.json()["id"]

    r = client.post(
        f"/api/v1/pesadas/{pesada_id}/salida",
        json={
            "peso_capturado": BASCULA["capacidad_max"] + 1000,
            "codigo_viaje": "V-5001", "peso_guia": 5000, "bultos": 5,
        },
        headers=headers_romana,
    )
    assert r.status_code == 400
    assert "capacidad" in r.json()["detail"].lower()
