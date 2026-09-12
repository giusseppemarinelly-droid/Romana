# ============================================================
# test_pesaje_manual.py — es_manual y procedencia
# ============================================================
# Comparación con el manual de usuario de Bigsoft (sistema anterior):
# permite tipear el peso a mano cuando la báscula no responde, marcado
# para trazabilidad. Simplificado a un solo flag por pesada (no por
# cada captura, ni la regla de "una vez manual, siempre manual" de
# Bigsoft) -- ver docstring de la migración a7b8c9d0e1f2.

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


def test_entrada_con_peso_manual_y_procedencia(client, headers_romana):
    vehiculo_id = _vehiculo_dedicado("TEST-MANUAL-001")

    r = client.post(
        "/api/v1/pesadas/entrada",
        json={
            "peso_bruto": 15000, "vehiculo_id": vehiculo_id, "tipo_pesaje": "GENERAL",
            "procedencia": "Finca El Baúl", "es_manual": True,
        },
        headers=headers_romana,
    )
    assert r.status_code == 200, r.text
    pesada = r.json()
    assert pesada["procedencia"] == "Finca El Baúl"
    assert pesada["es_manual"] is True


def test_entrada_sin_manual_por_defecto(client, headers_romana):
    vehiculo_id = _vehiculo_dedicado("TEST-MANUAL-002")

    r = client.post(
        "/api/v1/pesadas/entrada",
        json={"peso_bruto": 15000, "vehiculo_id": vehiculo_id, "tipo_pesaje": "GENERAL"},
        headers=headers_romana,
    )
    assert r.status_code == 200, r.text
    assert r.json()["es_manual"] is False
    assert r.json()["procedencia"] is None


def test_es_manual_se_mantiene_una_vez_marcado(client, headers_romana):
    """
    Si la entrada fue con báscula (es_manual=False) pero la salida se
    tipeó a mano, la pesada completa debe quedar marcada como manual --
    "al menos un peso no vino de la báscula", no "todos los pesos".
    """
    vehiculo_id = _vehiculo_dedicado("TEST-MANUAL-003")

    r = client.post(
        "/api/v1/pesadas/entrada",
        json={"peso_bruto": 15000, "vehiculo_id": vehiculo_id, "tipo_pesaje": "GENERAL"},
        headers=headers_romana,
    )
    pesada_id = r.json()["id"]
    assert r.json()["es_manual"] is False

    r = client.post(
        f"/api/v1/pesadas/{pesada_id}/salida",
        json={
            "peso_capturado": 20000, "codigo_viaje": "V-4001", "peso_guia": 5000, "bultos": 5,
            "es_manual": True,
        },
        headers=headers_romana,
    )
    assert r.status_code == 200, r.text
    assert r.json()["es_manual"] is True


def test_ticket_pdf_con_datos_nuevos_no_revienta(client, headers_romana):
    """
    Smoke test: el ticket PDF debe generarse sin excepción con
    procedencia, datos de guía y es_manual poblados -- no valida el
    contenido visual, solo que no rompe y produce un PDF real.
    """
    vehiculo_id = _vehiculo_dedicado("TEST-MANUAL-004")

    r = client.post(
        "/api/v1/pesadas/entrada",
        json={
            "peso_bruto": 15000, "vehiculo_id": vehiculo_id, "tipo_pesaje": "GENERAL",
            "procedencia": "Finca El Baúl", "es_manual": True,
        },
        headers=headers_romana,
    )
    pesada_id = r.json()["id"]

    client.post(
        f"/api/v1/pesadas/{pesada_id}/salida",
        json={"peso_capturado": 20000, "codigo_viaje": "V-4002", "peso_guia": 5000, "bultos": 5},
        headers=headers_romana,
    )

    r = client.get(f"/api/v1/reportes/ticket/{pesada_id}.pdf", headers=headers_romana)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 1000
