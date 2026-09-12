# ============================================================
# test_trazabilidad.py — I-05 (anular) e I-06 (completar)
# ============================================================
# I-05: anular_pesada() no recibía usuario_id -- la operación más
# sensible del sistema después del cierre no dejaba constancia de quién
# la hizo.
#
# I-06: completar_pesaje() pisaba las observaciones cargadas en la
# entrada (incluso con una cadena vacía) y reescribía usuario_salida_id
# con el usuario que completó, perdiendo quién había capturado el 2° peso.

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


def test_completar_no_pisa_observaciones_ni_usuario_salida(client, headers_romana, headers_cc, headers_admin):
    vehiculo_id = _vehiculo_dedicado("TEST-TRAZA-001")

    r = client.post(
        "/api/v1/pesadas/entrada",
        json={
            "peso_bruto": 15000, "vehiculo_id": vehiculo_id, "tipo_pesaje": "GENERAL",
            "observaciones": "Carga frágil, manejar con cuidado",
        },
        headers=headers_romana,
    )
    assert r.status_code == 200, r.text
    pesada_id = r.json()["id"]
    assert r.json()["observaciones"] == "Carga frágil, manejar con cuidado"

    # Captura de salida por "romana_test" -- diferencia de tolerancia
    # chica para que quede auto-aprobada y se pueda completar directo.
    r = client.post(
        f"/api/v1/pesadas/{pesada_id}/salida",
        json={"peso_capturado": 20000, "codigo_viaje": "V-3001", "peso_guia": 5000, "bultos": 5},
        headers=headers_romana,
    )
    assert r.status_code == 200, r.text
    assert r.json()["auto_aprobado"] is True

    # Completar por "admin_test" (usuario DISTINTO), sin mandar
    # observaciones -- no debe borrar lo que había.
    r = client.post(
        f"/api/v1/pesadas/{pesada_id}/completar",
        json={"peso_final": 20000},
        headers=headers_admin,
    )
    assert r.status_code == 200, r.text
    pesada = r.json()

    assert pesada["observaciones"] == "Carga frágil, manejar con cuidado", \
        "completar_pesaje() no debe pisar observaciones cuando no manda ninguna"
    assert pesada["usuario_salida"]["username"] == "romana_test", \
        "usuario_salida no debe cambiar al completar"
    assert pesada["usuario_completado"]["username"] == "admin_test", \
        "usuario_completado debe ser quien completó, no quien capturó la salida"


def test_completar_actualiza_observaciones_si_manda_una_nueva(client, headers_romana):
    vehiculo_id = _vehiculo_dedicado("TEST-TRAZA-002")

    r = client.post(
        "/api/v1/pesadas/entrada",
        json={"peso_bruto": 15000, "vehiculo_id": vehiculo_id, "tipo_pesaje": "GENERAL"},
        headers=headers_romana,
    )
    pesada_id = r.json()["id"]

    client.post(
        f"/api/v1/pesadas/{pesada_id}/salida",
        json={"peso_capturado": 20000, "codigo_viaje": "V-3002", "peso_guia": 5000, "bultos": 5},
        headers=headers_romana,
    )

    r = client.post(
        f"/api/v1/pesadas/{pesada_id}/completar",
        json={"peso_final": 20000, "observaciones": "Todo en orden"},
        headers=headers_romana,
    )
    assert r.status_code == 200, r.text
    assert r.json()["observaciones"] == "Todo en orden"


def test_anular_registra_usuario_y_fecha(client, headers_romana, headers_admin):
    vehiculo_id = _vehiculo_dedicado("TEST-TRAZA-003")

    r = client.post(
        "/api/v1/pesadas/entrada",
        json={"peso_bruto": 15000, "vehiculo_id": vehiculo_id, "tipo_pesaje": "GENERAL"},
        headers=headers_romana,
    )
    pesada_id = r.json()["id"]

    r = client.post(
        f"/api/v1/pesadas/{pesada_id}/anular",
        json={"motivo": "Camión se retiró sin cargar"},
        headers=headers_admin,
    )
    assert r.status_code == 200, r.text

    r = client.get(f"/api/v1/pesadas/{pesada_id}", headers=headers_romana)
    assert r.status_code == 200, r.text
    pesada = r.json()
    assert pesada["anulada"] is True
    assert pesada["anulado_por"]["username"] == "admin_test"
    assert pesada["fecha_anulacion"] is not None
