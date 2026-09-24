# ============================================================
# Comentario de Centro de Costos al aprobar (2026-09-24)
# ============================================================
# Al rechazar ya se exigía un motivo; ahora al aprobar se puede dejar
# (opcional) por qué se aprobó -- p. ej. una diferencia contra la guía
# que está justificada. Lo usan igual la web y la estación de escritorio.
import uuid

import pytest


@pytest.fixture
def pendiente_id(client, headers_romana):
    """Una pesada en `pendiente_aprobacion`, sobre un vehículo propio del
    test (un vehículo no puede tener dos pesadas activas a la vez)."""
    placa = f"CMT-{uuid.uuid4().hex[:6].upper()}"
    r = client.post("/api/v1/vehiculos", json={"placa": placa}, headers=headers_romana)
    assert r.status_code == 201, r.text
    vehiculo_id = r.json()["id"]

    r = client.post(
        "/api/v1/pesadas/entrada",
        json={"peso_bruto": 10000, "vehiculo_id": vehiculo_id, "tipo_pesaje": "GENERAL"},
        headers=headers_romana,
    )
    assert r.status_code == 200, r.text
    pesada_id = r.json()["id"]

    # neto 9000 contra guía 7000: fuera de tolerancia, va a la cola de CC.
    r = client.post(
        f"/api/v1/pesadas/{pesada_id}/salida",
        json={"peso_capturado": 19000, "codigo_viaje": "V-CMT", "peso_guia": 7000, "bultos": 10},
        headers=headers_romana,
    )
    assert r.json()["estado"] == "pendiente_aprobacion", r.text
    return pesada_id


def test_aprobar_con_comentario_lo_guarda(client, headers_cc, pendiente_id):
    r = client.post(
        f"/api/v1/pesadas/{pendiente_id}/aprobar",
        json={"comentario": "  Diferencia justificada: la guía traía el peso sin paletas.  "},
        headers=headers_cc,
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "aprobado"
    assert r.json()["comentario_aprobacion"] == "Diferencia justificada: la guía traía el peso sin paletas."

    # Y queda en la pesada, no solo en la respuesta.
    r = client.get(f"/api/v1/pesadas/{pendiente_id}", headers=headers_cc)
    assert r.json()["comentario_aprobacion"].startswith("Diferencia justificada")


def test_aprobar_sin_cuerpo_sigue_andando(client, headers_cc, pendiente_id):
    # Compatibilidad: una estación de escritorio sin actualizar sigue
    # mandando el POST sin cuerpo.
    r = client.post(f"/api/v1/pesadas/{pendiente_id}/aprobar", headers=headers_cc)
    assert r.status_code == 200, r.text
    assert r.json()["comentario_aprobacion"] is None


def test_comentario_en_blanco_se_guarda_como_vacio(client, headers_cc, pendiente_id):
    r = client.post(
        f"/api/v1/pesadas/{pendiente_id}/aprobar", json={"comentario": "   "}, headers=headers_cc
    )
    assert r.status_code == 200, r.text
    assert r.json()["comentario_aprobacion"] is None


def test_rechazar_sigue_exigiendo_motivo(client, headers_cc, pendiente_id):
    r = client.post(f"/api/v1/pesadas/{pendiente_id}/rechazar", json={"motivo": ""}, headers=headers_cc)
    assert r.status_code == 400

    r = client.post(
        f"/api/v1/pesadas/{pendiente_id}/rechazar",
        json={"motivo": "El neto no coincide con lo cargado"},
        headers=headers_cc,
    )
    assert r.status_code == 200, r.text
    assert r.json()["motivo_rechazo"] == "El neto no coincide con lo cargado"
