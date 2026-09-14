# ============================================================
# test_limpieza_menor.py — M-03 (doble conteo en el corte) y M-04 (tolerancia sin try)
# ============================================================

import datetime as datetime_mod

from database.engine import SessionLocal
from database.models import Vehiculo, Pesada, Corte, Usuario
from services import pesaje_service


def test_corte_no_cuenta_dos_veces_una_pesada_en_el_borde(monkeypatch):
    """
    Hallazgo M-03: el filtro de fecha era >= inicio Y <= fin, ambos
    inclusive -- una pesada con fecha_salida EXACTO en el instante de
    corte quedaba contada en los dos cortes consecutivos que comparten
    ese instante como frontera.
    """
    borde = datetime_mod.datetime(2026, 1, 1, 12, 0, 0)
    antes = borde - datetime_mod.timedelta(hours=2)
    despues = borde + datetime_mod.timedelta(hours=1)

    db = SessionLocal()
    try:
        admin = db.query(Usuario).filter_by(username="admin_test").first()

        vehiculo = Vehiculo(placa="TEST-CORTE-BORDE", descripcion="Solo para este test", activo=True)
        db.add(vehiculo)
        db.commit()
        db.refresh(vehiculo)

        pesada = Pesada(
            numero_ticket="TK-CORTE-BORDE-TEST", estado="completado", tipo_pesaje="GENERAL",
            vehiculo_id=vehiculo.id,
            peso_entrada=10000, peso_bruto=15000, peso_tara=10000, peso_neto=5000,
            fecha_entrada=borde, fecha_salida=borde, anulada=False,
        )
        db.add(pesada)

        # Corte previo con un número bien alto para no chocar con el
        # contador real (services/pesaje_service usa "corte_actual" en
        # Configuracion, no MAX(numero_corte) -- no toca este número).
        # Así el primer realizar_corte() de este test arranca justo en
        # "antes", sin depender de qué corte haya hecho algún otro test.
        corte_previo = Corte(
            numero_corte=999000, fecha_inicio=antes - datetime_mod.timedelta(hours=1),
            fecha_fin=antes, total_pesadas=0, total_neto_kg=0, usuario_id=admin.id,
        )
        db.add(corte_previo)
        db.commit()
    finally:
        db.close()

    class _RelojControlado(datetime_mod.datetime):
        # realizar_corte() llama datetime.now() dos veces por invocación
        # (fecha_fin, y después created_at del Corte nuevo) -- se repite
        # cada valor para cubrir las dos.
        _cola = [borde, borde, despues, despues]

        @classmethod
        def now(cls, tz=None):
            return cls._cola.pop(0)

    monkeypatch.setattr(pesaje_service, "datetime", _RelojControlado)

    r1 = pesaje_service.realizar_corte(usuario_id=admin.id)  # fecha_fin = borde
    r2 = pesaje_service.realizar_corte(usuario_id=admin.id)  # fecha_inicio = borde, fecha_fin = despues

    assert r1["exito"] and r2["exito"]
    total_entre_ambos = r1["total_pesadas"] + r2["total_pesadas"]
    assert total_entre_ambos == 1, f"la pesada del borde se contó {total_entre_ambos} veces (debería ser 1)"
    assert r2["total_pesadas"] == 1, "el instante del borde debe pertenecer al corte que EMPIEZA ahí, no al que termina"


def test_tolerancia_mal_configurada_no_tumba_la_captura(client, headers_romana, monkeypatch):
    """
    Hallazgo M-04: antes float(_get_config(...)) no tenía try -- un
    valor con coma decimal en vez de punto en la configuración de
    tolerancia tumbaba TODA captura de salida con un error genérico.
    """
    from database.engine import SessionLocal as _SL
    from database.models import Configuracion

    db = _SL()
    try:
        cfg = db.query(Configuracion).filter_by(clave="tolerancia_aprobacion_pct").first()
        if cfg:
            cfg.valor = "10,5"  # coma en vez de punto -- valor mal escrito
        else:
            db.add(Configuracion(clave="tolerancia_aprobacion_pct", valor="10,5"))
        db.commit()
    finally:
        db.close()

    db = _SL()
    try:
        v = Vehiculo(placa="TEST-M04", descripcion="Solo para este test", activo=True)
        db.add(v)
        db.commit()
        db.refresh(v)
        vehiculo_id = v.id
    finally:
        db.close()

    r = client.post(
        "/api/v1/pesadas/entrada",
        json={"peso_bruto": 15000, "vehiculo_id": vehiculo_id, "tipo_pesaje": "GENERAL"},
        headers=headers_romana,
    )
    pesada_id = r.json()["id"]

    r = client.post(
        f"/api/v1/pesadas/{pesada_id}/salida",
        json={"peso_capturado": 20000, "codigo_viaje": "V-M04", "peso_guia": 5000, "bultos": 5},
        headers=headers_romana,
    )
    assert r.status_code == 200, r.text  # con el fix, no revienta pese a la config mal escrita

    # Limpiar para no afectar otros tests que sí esperan el default de 10%.
    db = _SL()
    try:
        cfg = db.query(Configuracion).filter_by(clave="tolerancia_aprobacion_pct").first()
        if cfg:
            cfg.valor = "10"
            db.commit()
    finally:
        db.close()
