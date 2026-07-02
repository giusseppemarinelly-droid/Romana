# ============================================================
# backend/tests/test_flujo_pesaje.py
# ============================================================
# Verifica end-to-end la máquina de estados de Pesada tal como la
# recorren las dos estaciones físicas (Romana y Centro de Costos),
# más los mandatos de arquitectura del proyecto: permisos por nivel,
# inmutabilidad de pesajes cerrados, y seguridad ante concurrencia.
from concurrent.futures import ThreadPoolExecutor

from services import pesaje_service


def test_flujo_completo_entrada_a_completado(client, headers_romana, headers_cc, headers_admin, vehiculo_id):
    # 1. Romana registra la entrada (Tara) — estado inicial "en_planta".
    r = client.post(
        "/api/v1/pesadas/entrada",
        json={"peso_bruto": 15000, "vehiculo_id": vehiculo_id, "tipo_pesaje": "GENERAL"},
        headers=headers_romana,
    )
    assert r.status_code == 200, r.text
    pesada = r.json()
    assert pesada["estado"] == "en_planta"
    pesada_id = pesada["id"]

    # 2. Romana captura el 2° peso (peso bruto real) — pasa a "pendiente_aprobacion"
    #    y el neto se calcula automáticamente (mayor - menor de los dos pesajes).
    r = client.post(
        f"/api/v1/pesadas/{pesada_id}/salida",
        json={"peso_capturado": 25000},
        headers=headers_romana,
    )
    assert r.status_code == 200, r.text
    pesada = r.json()
    assert pesada["estado"] == "pendiente_aprobacion"
    assert pesada["peso_bruto"] == 25000
    assert pesada["peso_tara"] == 15000
    assert pesada["peso_neto"] == 10000

    # 3. Centro de Costos aprueba — pasa a "aprobado".
    r = client.post(f"/api/v1/pesadas/{pesada_id}/aprobar", headers=headers_cc)
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "aprobado"

    # 4. Aprobar de nuevo debe fallar: ya no está en "pendiente_aprobacion".
    r = client.post(f"/api/v1/pesadas/{pesada_id}/aprobar", headers=headers_cc)
    assert r.status_code == 400

    # 5. Romana completa los datos finales — pasa a "completado".
    r = client.post(
        f"/api/v1/pesadas/{pesada_id}/completar",
        json={"orden_compra": "OC-123", "cantidad": 10000},
        headers=headers_romana,
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "completado"

    # 6. Inmutabilidad: una pesada completada no se puede volver a completar...
    r = client.post(f"/api/v1/pesadas/{pesada_id}/completar", json={}, headers=headers_romana)
    assert r.status_code == 400

    # ...ni anular (mandato: registros cerrados son inmutables). Se usa
    # headers_admin porque "pesaje_anular" solo lo tienen niveles 1 y 2 —
    # este assert prueba la regla de negocio (estado), no el permiso.
    r = client.post(
        f"/api/v1/pesadas/{pesada_id}/anular",
        json={"motivo": "intento de alterar un registro cerrado"},
        headers=headers_admin,
    )
    assert r.status_code == 400
    assert "inmutable" in r.json()["detail"].lower() or "completada" in r.json()["detail"].lower()


def test_permisos_por_nivel_operador_no_puede_aprobar(client, headers_romana, headers_cc, vehiculo_id):
    r = client.post(
        "/api/v1/pesadas/entrada",
        json={"peso_bruto": 12000, "vehiculo_id": vehiculo_id, "tipo_pesaje": "GENERAL"},
        headers=headers_romana,
    )
    assert r.status_code == 200, r.text
    pesada_id = r.json()["id"]

    r = client.post(f"/api/v1/pesadas/{pesada_id}/salida", json={"peso_capturado": 20000}, headers=headers_romana)
    assert r.status_code == 200, r.text

    # Un operador de Romana (nivel 3) no tiene permiso "centro_costos".
    r = client.post(f"/api/v1/pesadas/{pesada_id}/aprobar", headers=headers_romana)
    assert r.status_code == 403

    # Centro de Costos (nivel 4) no tiene permiso "pesaje_entrada".
    r = client.post(
        "/api/v1/pesadas/entrada",
        json={"peso_bruto": 12000, "vehiculo_id": vehiculo_id, "tipo_pesaje": "GENERAL"},
        headers=headers_cc,
    )
    assert r.status_code == 403

    # limpieza: dejar el vehículo libre para no interferir con otros tests
    r = client.post(f"/api/v1/pesadas/{pesada_id}/aprobar", headers=headers_cc)
    assert r.status_code == 200
    client.post(f"/api/v1/pesadas/{pesada_id}/completar", json={}, headers=headers_romana)


def test_no_se_puede_registrar_dos_pesadas_activas_para_el_mismo_vehiculo(client, headers_romana, vehiculo_b_id):
    r = client.post(
        "/api/v1/pesadas/entrada",
        json={"peso_bruto": 10000, "vehiculo_id": vehiculo_b_id, "tipo_pesaje": "GENERAL"},
        headers=headers_romana,
    )
    assert r.status_code == 200, r.text

    r = client.post(
        "/api/v1/pesadas/entrada",
        json={"peso_bruto": 11000, "vehiculo_id": vehiculo_b_id, "tipo_pesaje": "GENERAL"},
        headers=headers_romana,
    )
    assert r.status_code == 400
    assert "activa" in r.json()["detail"].lower()


def test_concurrencia_solo_una_entrada_gana_la_carrera():
    """
    Llama services.pesaje_service.registrar_entrada directamente (sin pasar
    por HTTP) desde varios hilos a la vez para el mismo vehículo, simulando
    dos operadores/requests concurrentes. El chequeo previo en el servicio
    es check-then-act y por sí solo NO evita la carrera; lo que realmente
    la cierra es el índice único parcial ux_pesada_activa_por_vehiculo
    (ver database/migrations/versions/*_indice_unico_pesada_activa*.py).
    """
    from database.engine import SessionLocal
    from database.models import Vehiculo

    db = SessionLocal()
    try:
        vehiculo = Vehiculo(placa="TEST-CONCURRENCIA", descripcion="Solo para este test", activo=True)
        db.add(vehiculo)
        db.commit()
        db.refresh(vehiculo)
        vehiculo_id = vehiculo.id
    finally:
        db.close()

    def _intentar_entrada(_):
        return pesaje_service.registrar_entrada(
            peso_bruto=10000, vehiculo_id=vehiculo_id, tipo_pesaje="GENERAL"
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        resultados = list(pool.map(_intentar_entrada, range(8)))

    exitosos = [r for r in resultados if r["exito"]]
    assert len(exitosos) == 1, f"Se esperaba exactamente 1 éxito, hubo {len(exitosos)}: {resultados}"
