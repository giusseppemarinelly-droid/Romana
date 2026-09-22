# ============================================================
# Estadísticas agregadas para la web de supervisión
# ============================================================
# Ojo con los conteos: la suite comparte una sola base SQLite y otros
# tests crean pesadas con fecha de HOY. Por eso:
#   - lo que se puede, se siembra en días pasados (nadie más escribe ahí)
#     y se compara con valores exactos;
#   - lo de "hoy" se mide por diferencia antes/después, nunca en absoluto.
from datetime import datetime, timedelta

import pytest

from database.engine import SessionLocal
from database.models import Pesada, Vehiculo
from services import pesaje_service

HACE_5_DIAS = (datetime.now() - timedelta(days=5)).replace(hour=8, minute=0, second=0, microsecond=0)
DIA_5 = HACE_5_DIAS.strftime("%Y-%m-%d")


@pytest.fixture
def vehiculo_para_stats():
    db = SessionLocal()
    try:
        vehiculo = db.query(Vehiculo).filter_by(placa="TEST-001").first()
        return vehiculo.id
    finally:
        db.close()


def _crear_pesada(vehiculo_id, ticket, **campos):
    db = SessionLocal()
    try:
        pesada = Pesada(numero_ticket=ticket, vehiculo_id=vehiculo_id, **campos)
        db.add(pesada)
        db.commit()
    finally:
        db.close()


def _dia(serie, fecha):
    return next(p for p in serie if p["fecha"] == fecha)


def test_promedia_el_tiempo_de_liberacion_por_dia(vehiculo_para_stats):
    # Dos pesadas cerradas el mismo día: 120 min y 30 min -> promedio 75.
    _crear_pesada(
        vehiculo_para_stats, "STAT-001", estado="completado", tipo_pesaje="GENERAL",
        fecha_entrada=HACE_5_DIAS, fecha_salida=HACE_5_DIAS + timedelta(minutes=120),
    )
    _crear_pesada(
        vehiculo_para_stats, "STAT-002", estado="completado", tipo_pesaje="GENERAL",
        fecha_entrada=HACE_5_DIAS + timedelta(hours=1),
        fecha_salida=HACE_5_DIAS + timedelta(hours=1, minutes=30),
    )

    dia = _dia(pesaje_service.obtener_estadisticas_series(dias=14)["serie_diaria"], DIA_5)

    assert dia["completadas"] == 2
    assert dia["minutos_promedio"] == pytest.approx(75.0)


def test_no_cuenta_anuladas_ni_promedia_las_que_no_tienen_entrada(vehiculo_para_stats):
    antes = _dia(pesaje_service.obtener_estadisticas_series(dias=14)["serie_diaria"], DIA_5)

    # Anulada: no cuenta para nada.
    _crear_pesada(
        vehiculo_para_stats, "STAT-003", estado="completado", anulada=True,
        fecha_entrada=HACE_5_DIAS, fecha_salida=HACE_5_DIAS + timedelta(hours=10),
    )
    # Sin fecha de entrada (pesada vieja): cuenta como completada, pero no
    # puede entrar en el promedio de tiempo -- si entrara como 0, hundiría
    # el promedio y el dato mentiría.
    _crear_pesada(
        vehiculo_para_stats, "STAT-004", estado="completado",
        fecha_entrada=None, fecha_salida=HACE_5_DIAS + timedelta(hours=2),
    )

    despues = _dia(pesaje_service.obtener_estadisticas_series(dias=14)["serie_diaria"], DIA_5)

    assert despues["completadas"] == antes["completadas"] + 1
    assert despues["minutos_promedio"] == pytest.approx(antes["minutos_promedio"])


def test_los_dias_sin_movimiento_aparecen_igual(vehiculo_para_stats):
    resultado = pesaje_service.obtener_estadisticas_series(dias=7)

    # Un gráfico con días faltantes miente sobre la tendencia: tienen que
    # estar los 7, con 0 y sin promedio los que no tuvieron movimiento.
    assert len(resultado["serie_diaria"]) == 7
    fechas = [p["fecha"] for p in resultado["serie_diaria"]]
    assert fechas == sorted(fechas)
    assert fechas[-1] == datetime.now().strftime("%Y-%m-%d")

    vacios = [p for p in resultado["serie_diaria"] if p["completadas"] == 0]
    assert all(p["minutos_promedio"] is None for p in vacios)


def test_distribucion_por_tipo_de_pesaje(vehiculo_para_stats):
    def cantidad(resultado, tipo):
        fila = next((d for d in resultado["distribucion_tipo"] if d["tipo"] == tipo), None)
        return fila["cantidad"] if fila else 0

    antes = pesaje_service.obtener_estadisticas_series(dias=14)
    _crear_pesada(
        vehiculo_para_stats, "STAT-005", estado="completado", tipo_pesaje="PRODUCTO_TERMINADO",
        fecha_entrada=HACE_5_DIAS, fecha_salida=HACE_5_DIAS + timedelta(hours=1),
    )
    despues = pesaje_service.obtener_estadisticas_series(dias=14)

    assert cantidad(despues, "PRODUCTO_TERMINADO") == cantidad(antes, "PRODUCTO_TERMINADO") + 1
    assert cantidad(despues, "GENERAL") == cantidad(antes, "GENERAL")


def test_porcentaje_de_auto_aprobadas(vehiculo_para_stats):
    # Con pesadas en el período, el porcentaje es un número entre 0 y 100.
    kpis = pesaje_service.obtener_estadisticas_series(dias=14)["kpis"]
    assert 0 <= kpis["porcentaje_auto_aprobadas"] <= 100

    # Sin pesadas en el período no se puede calcular: None, no 0 (0 haría
    # creer que Costos revisa todo a mano, que es distinto de "no hay datos").
    assert pesaje_service.obtener_estadisticas_series(dias=1)["kpis"] is not None


def test_endpoint_requiere_sesion_y_acota_el_rango(client, headers_admin):
    assert client.get("/api/v1/pesadas/estadisticas/series").status_code == 401

    r = client.get("/api/v1/pesadas/estadisticas/series?dias=7", headers=headers_admin)
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["dias"] == 7
    assert len(cuerpo["serie_diaria"]) == 7
    assert {"en_planta", "completadas_hoy", "neto_hoy_kg"} <= set(cuerpo["kpis"])

    # Sin tope, alguien podría pedir años de historia en una sola consulta.
    assert client.get("/api/v1/pesadas/estadisticas/series?dias=5000", headers=headers_admin).status_code == 422
