# ============================================================
# test_rechazo_recaptura.py — C-01: rechazo → re-captura
# ============================================================
# Hallazgo crítico de la auditoría (commit c97fdcc), reproducido en
# pruebas de campo: peso_bruto cumplía dos funciones incompatibles --
# guardaba el peso de entrada al registrar la entrada, y se
# sobrescribía en cada captura de salida. En una re-captura tras un
# rechazo de Centro de Costos, el peso de entrada original ya se había
# perdido: el neto quedaba calculado contra el bruto de la captura
# rechazada, no contra la entrada real.
#
# Ninguno de los tests existentes recorría este camino -- es
# precisamente para lo que existe el estado "rechazado".

from database.engine import SessionLocal
from database.models import Vehiculo
from services import pesaje_service


def _vehiculo_dedicado(placa: str) -> int:
    # Vehículo propio (no los fixtures compartidos) para no interferir
    # con otros tests que reutilizan vehiculo_id/vehiculo_b_id.
    db = SessionLocal()
    try:
        v = Vehiculo(placa=placa, descripcion="Solo para este test", activo=True)
        db.add(v)
        db.commit()
        db.refresh(v)
        return v.id
    finally:
        db.close()


def test_recaptura_tras_rechazo_no_pierde_el_peso_de_entrada(client, headers_romana, headers_cc):
    vehiculo_id = _vehiculo_dedicado("TEST-RECAPTURA-001")

    # 1. Entrada real: 15.000 kg.
    r = client.post(
        "/api/v1/pesadas/entrada",
        json={"peso_bruto": 15000, "vehiculo_id": vehiculo_id, "tipo_pesaje": "GENERAL"},
        headers=headers_romana,
    )
    assert r.status_code == 200, r.text
    pesada_id = r.json()["id"]
    assert r.json()["peso_entrada"] == 15000

    # 2. Primera captura de salida: 40.000 kg, con un peso_guia que fuerza
    #    diferencia fuera de tolerancia -> pendiente_aprobacion.
    r = client.post(
        f"/api/v1/pesadas/{pesada_id}/salida",
        json={"peso_capturado": 40000, "codigo_viaje": "V-2001", "peso_guia": 15000, "bultos": 10},
        headers=headers_romana,
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "pendiente_aprobacion"
    assert r.json()["peso_entrada"] == 15000  # no debe cambiar nunca

    # 3. Centro de Costos rechaza.
    r = client.post(
        f"/api/v1/pesadas/{pesada_id}/rechazar",
        json={"motivo": "Diferencia demasiado alta, verificar"},
        headers=headers_cc,
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "rechazado"
    assert r.json()["peso_entrada"] == 15000  # tampoco cambia con el rechazo

    # 4. Romana vuelve a capturar: 40.100 kg.
    r = client.post(
        f"/api/v1/pesadas/{pesada_id}/salida",
        json={"peso_capturado": 40100, "codigo_viaje": "V-2001", "peso_guia": 100, "bultos": 10},
        headers=headers_romana,
    )
    assert r.status_code == 200, r.text
    pesada = r.json()

    # El bug (C-01): peso_bruto de la captura RECHAZADA (40000) quedaba
    # pisando lo que se usaba como "peso de entrada" en el cálculo, y el
    # neto salía ~100 kg en vez de ~25.100 kg.
    assert pesada["peso_entrada"] == 15000, "peso_entrada debe seguir siendo el de la entrada real"
    assert pesada["peso_tara"] == 15000, "la tara debe seguir siendo el peso de entrada real"
    assert pesada["peso_bruto"] == 40100, "el bruto debe ser la 2ª captura (la válida), no la rechazada"
    assert pesada["peso_neto"] == 25100, f"neto incorrecto: {pesada['peso_neto']} (bug reproducido si da ~100)"
