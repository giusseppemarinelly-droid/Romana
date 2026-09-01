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
    # peso_guia=8000 → diferencia de 25% contra el neto (10000), por
    # encima de la tolerancia por defecto (10%): queda pendiente de
    # revisión manual, que es justo lo que este test quiere ejercitar.
    r = client.post(
        f"/api/v1/pesadas/{pesada_id}/salida",
        json={"peso_capturado": 25000, "codigo_viaje": "V-1001", "peso_guia": 8000, "bultos": 40},
        headers=headers_romana,
    )
    assert r.status_code == 200, r.text
    pesada = r.json()
    assert pesada["estado"] == "pendiente_aprobacion"
    assert pesada["auto_aprobado"] is False
    assert pesada["peso_bruto"] == 25000
    assert pesada["peso_tara"] == 15000
    assert pesada["peso_neto"] == 10000
    assert pesada["codigo_viaje"] == "V-1001"
    assert pesada["peso_guia"] == 8000
    assert pesada["bultos"] == 40

    # 3. Centro de Costos aprueba — pasa a "aprobado".
    r = client.post(f"/api/v1/pesadas/{pesada_id}/aprobar", headers=headers_cc)
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "aprobado"

    # 4. Aprobar de nuevo debe fallar: ya no está en "pendiente_aprobacion".
    r = client.post(f"/api/v1/pesadas/{pesada_id}/aprobar", headers=headers_cc)
    assert r.status_code == 400

    # 5. Romana captura el peso final (3er pesaje, antes de autorizar la
    #    salida) y completa los datos finales — pasa a "completado".
    r = client.post(
        f"/api/v1/pesadas/{pesada_id}/completar",
        json={"peso_final": 25000, "orden_compra": "OC-123", "cantidad": 10000},
        headers=headers_romana,
    )
    assert r.status_code == 200, r.text
    pesada = r.json()
    assert pesada["estado"] == "completado"
    assert pesada["peso_final"] == 25000

    # 6. Inmutabilidad: una pesada completada no se puede volver a completar...
    r = client.post(
        f"/api/v1/pesadas/{pesada_id}/completar",
        json={"peso_final": 25000}, headers=headers_romana,
    )
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

    # peso_guia=6000 → diferencia de 33.3% contra el neto (8000): fuera
    # de tolerancia, sigue el camino de revisión manual que este test
    # necesita (más abajo llama a /aprobar explícitamente).
    r = client.post(
        f"/api/v1/pesadas/{pesada_id}/salida",
        json={"peso_capturado": 20000, "codigo_viaje": "V-2002", "peso_guia": 6000, "bultos": 15},
        headers=headers_romana,
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "pendiente_aprobacion"

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
    client.post(f"/api/v1/pesadas/{pesada_id}/completar", json={"peso_final": 20000}, headers=headers_romana)


def test_auto_aprobacion_dentro_de_tolerancia(client, headers_romana, vehiculo_id):
    """
    Si la diferencia entre peso_guia y el neto capturado está por debajo
    de la tolerancia configurada (10% por defecto), la pesada se aprueba
    sola -- sin que Centro de Costos tenga que llamar a /aprobar.
    """
    r = client.post(
        "/api/v1/pesadas/entrada",
        json={"peso_bruto": 12000, "vehiculo_id": vehiculo_id, "tipo_pesaje": "GENERAL"},
        headers=headers_romana,
    )
    assert r.status_code == 200, r.text
    pesada_id = r.json()["id"]

    # neto = 20000 - 12000 = 8000; peso_guia=7800 → diferencia ~2.56%, dentro de tolerancia.
    r = client.post(
        f"/api/v1/pesadas/{pesada_id}/salida",
        json={"peso_capturado": 20000, "codigo_viaje": "V-3003", "peso_guia": 7800, "bultos": 25},
        headers=headers_romana,
    )
    assert r.status_code == 200, r.text
    pesada = r.json()
    assert pesada["estado"] == "aprobado"
    assert pesada["auto_aprobado"] is True
    assert pesada["aprobado_por"] is None  # nadie de CC decidió, fue automático
    assert pesada["codigo_viaje"] == "V-3003"
    assert pesada["peso_guia"] == 7800
    assert pesada["bultos"] == 25

    # Romana puede completar directo, sin que CC haya tocado nada.
    r = client.post(
        f"/api/v1/pesadas/{pesada_id}/completar",
        json={"peso_final": 20000}, headers=headers_romana,
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "completado"


def test_diferencia_fuera_de_tolerancia_requiere_aprobacion_manual(client, headers_romana, headers_cc, vehiculo_id):
    """Complemento del test anterior: por encima de la tolerancia, sigue
    yendo a la cola accionable de Centro de Costos como hasta ahora."""
    r = client.post(
        "/api/v1/pesadas/entrada",
        json={"peso_bruto": 10000, "vehiculo_id": vehiculo_id, "tipo_pesaje": "GENERAL"},
        headers=headers_romana,
    )
    assert r.status_code == 200, r.text
    pesada_id = r.json()["id"]

    # neto = 19000 - 10000 = 9000; peso_guia=7000 → diferencia ~28.6%, fuera de tolerancia.
    r = client.post(
        f"/api/v1/pesadas/{pesada_id}/salida",
        json={"peso_capturado": 19000, "codigo_viaje": "V-4004", "peso_guia": 7000, "bultos": 10},
        headers=headers_romana,
    )
    assert r.status_code == 200, r.text
    pesada = r.json()
    assert pesada["estado"] == "pendiente_aprobacion"
    assert pesada["auto_aprobado"] is False

    r = client.post(f"/api/v1/pesadas/{pesada_id}/aprobar", headers=headers_cc)
    assert r.status_code == 200, r.text
    assert r.json()["auto_aprobado"] is False

    client.post(f"/api/v1/pesadas/{pesada_id}/completar", json={"peso_final": 19000}, headers=headers_romana)


def test_recaptura_tras_rechazo_conserva_el_peso_de_entrada(client, headers_romana, headers_cc, vehiculo_c_id):
    """
    Regresión: `peso_bruto` servía a la vez de "peso de entrada" y de "bruto
    final", así que la primera captura lo sobrescribía con el mayor de los dos
    pesajes y el peso de entrada se perdía. Al re-capturar tras un rechazo de
    Centro de Costos -- el camino que el estado "rechazado" existe para
    recorrer -- el neto se calculaba contra el bruto anterior en vez de contra
    la entrada: con entrada 15.000 y capturas de 40.000 → 40.100 el neto daba
    100 KG en vez de 25.100, y el peso de entrada quedaba irrecuperable.

    El peso de entrada vive ahora en su propia columna `peso_entrada`, que se
    escribe una sola vez en la entrada y no se toca nunca más.
    """
    r = client.post(
        "/api/v1/pesadas/entrada",
        json={"peso_bruto": 15000, "vehiculo_id": vehiculo_c_id, "tipo_pesaje": "GENERAL"},
        headers=headers_romana,
    )
    assert r.status_code == 200, r.text
    pesada_id = r.json()["id"]
    assert r.json()["peso_entrada"] == 15000

    # 1ª captura: neto 25.000 contra una guía de 15.000 → 66.7%, fuera de
    # tolerancia, así que va a la cola accionable de Centro de Costos.
    r = client.post(
        f"/api/v1/pesadas/{pesada_id}/salida",
        json={"peso_capturado": 40000, "codigo_viaje": "V-5005", "peso_guia": 15000, "bultos": 20},
        headers=headers_romana,
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "pendiente_aprobacion"
    assert r.json()["peso_neto"] == 25000

    # Centro de Costos rechaza: Romana tiene que volver a pesar.
    r = client.post(
        f"/api/v1/pesadas/{pesada_id}/rechazar",
        json={"motivo": "peso dudoso, repetir el pesaje"},
        headers=headers_cc,
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "rechazado"
    # La entrada sobrevive intacta a la primera captura y al rechazo.
    assert r.json()["peso_entrada"] == 15000

    # 2ª captura, casi el mismo peso que la primera.
    r = client.post(
        f"/api/v1/pesadas/{pesada_id}/salida",
        json={"peso_capturado": 40100, "codigo_viaje": "V-5005", "peso_guia": 25000, "bultos": 20},
        headers=headers_romana,
    )
    assert r.status_code == 200, r.text
    pesada = r.json()

    assert pesada["peso_entrada"] == 15000, "el peso de entrada nunca se sobrescribe"
    assert pesada["peso_tara"] == 15000, "la tara sigue siendo la entrada, no el bruto anterior"
    assert pesada["peso_bruto"] == 40100
    assert pesada["peso_neto"] == 25100, "el neto se calcula contra la entrada, no contra el bruto anterior"

    # limpieza: dejar el vehículo libre para no interferir con otros tests
    client.post(f"/api/v1/pesadas/{pesada_id}/aprobar", headers=headers_cc)
    client.post(f"/api/v1/pesadas/{pesada_id}/completar",
                json={"peso_final": 40100}, headers=headers_romana)


def test_no_se_puede_recapturar_una_pesada_anterior_a_peso_entrada(client, headers_romana):
    """
    Filas migradas desde antes de que existiera `peso_entrada`: si ya habían
    sido capturadas, su peso de entrada es irrecuperable (peso_bruto/peso_tara
    quedaron como mayor/menor, sin registro de cuál de los dos fue la entrada).
    La captura debe negarse con un mensaje accionable en vez de calcular un
    neto contra el número equivocado -- que es exactamente el bug que esta
    columna vino a cerrar.
    """
    from database.engine import SessionLocal
    from database.models import Pesada, Vehiculo

    db = SessionLocal()
    try:
        vehiculo = Vehiculo(placa="TEST-LEGADO", descripcion="Fila pre-migración", activo=True)
        db.add(vehiculo)
        db.commit()
        db.refresh(vehiculo)

        # Estado en que la migración deja una fila ya capturada: sin peso_entrada.
        legado = Pesada(
            numero_ticket="TK-LEGADO", estado="rechazado", tipo_pesaje="GENERAL",
            peso_entrada=None, peso_bruto=22300, peso_tara=8900, peso_neto=13400,
            vehiculo_id=vehiculo.id, motivo_rechazo="rechazada antes de la migración",
        )
        db.add(legado)
        db.commit()
        db.refresh(legado)
        pesada_id = legado.id
    finally:
        db.close()

    r = client.post(
        f"/api/v1/pesadas/{pesada_id}/salida",
        json={"peso_capturado": 22400, "codigo_viaje": "V-6006", "peso_guia": 13000, "bultos": 5},
        headers=headers_romana,
    )
    assert r.status_code == 400
    assert "peso de entrada" in r.json()["detail"].lower()


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


def test_las_lecturas_de_pesadas_exigen_autenticacion(client):
    """
    Regresión: los GET de listados, kardex y estadísticas se escribieron sin
    dependency de autenticación y respondían 200 sin token. Con
    `API_HOST=0.0.0.0` y CORS abierto, cualquier máquina de la red de planta
    podía descargar el histórico completo de operaciones sin credenciales.
    """
    rutas_lectura = [
        "/api/v1/pesadas/en-planta",
        "/api/v1/pesadas/aprobadas-pendientes",
        "/api/v1/pesadas/completadas",
        "/api/v1/pesadas/estadisticas",
        "/api/v1/pesadas/kardex/buscar",
        "/api/v1/pesadas/vehiculo/1/activa",
        "/api/v1/pesadas/1",
    ]
    for ruta in rutas_lectura:
        assert client.get(ruta).status_code == 401, f"{ruta} responde sin token"


def test_las_lecturas_siguen_disponibles_para_los_cuatro_niveles(
    client, headers_admin, headers_romana, headers_cc
):
    """
    Complemento del test anterior: cerrar el hueco no debe restringir por rol.
    Dashboard y kardex los consultan los cuatro niveles, así que exigir un
    permiso concreto en vez de solo autenticación rompería esas pantallas.
    """
    for headers in (headers_admin, headers_romana, headers_cc):
        assert client.get("/api/v1/pesadas/en-planta", headers=headers).status_code == 200
        assert client.get("/api/v1/pesadas/estadisticas", headers=headers).status_code == 200
        assert client.get("/api/v1/pesadas/kardex/buscar", headers=headers).status_code == 200
