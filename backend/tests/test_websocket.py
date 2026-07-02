# ============================================================
# backend/tests/test_websocket.py
# ============================================================
# Verifica que el canal /ws/pesadas efectivamente empuja el evento que
# permite el refresco automático de la cola en Centro de Costos apenas
# Romana captura el peso de salida — el caso de uso central de la
# migración a tiempo real.
from database.engine import SessionLocal
from database.models import Vehiculo


def _crear_vehiculo(placa: str) -> int:
    db = SessionLocal()
    try:
        v = Vehiculo(placa=placa, descripcion="Vehículo de prueba WS", activo=True)
        db.add(v)
        db.commit()
        db.refresh(v)
        return v.id
    finally:
        db.close()


def test_ws_notifica_pendiente_aprobacion_al_capturar_salida(client, headers_romana, token_romana):
    vehiculo_id = _crear_vehiculo("TEST-WS-001")

    r = client.post(
        "/api/v1/pesadas/entrada",
        json={"peso_bruto": 9000, "vehiculo_id": vehiculo_id, "tipo_pesaje": "GENERAL"},
        headers=headers_romana,
    )
    assert r.status_code == 200, r.text
    pesada_id = r.json()["id"]

    with client.websocket_connect(f"/ws/pesadas?token={token_romana}") as ws:
        r = client.post(
            f"/api/v1/pesadas/{pesada_id}/salida",
            json={"peso_capturado": 18000},
            headers=headers_romana,
        )
        assert r.status_code == 200, r.text

        evento = ws.receive_json()
        assert evento["tipo"] == "pesada_pendiente_aprobacion"
        assert evento["pesada_id"] == pesada_id


def test_ws_rechaza_conexion_sin_token_valido(client):
    import pytest
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/pesadas?token=token-invalido"):
            pass
