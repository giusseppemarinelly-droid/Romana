# ============================================================
# test_errores_no_filtran_detalle.py — I-10
# ============================================================
# Antes, cada función de servicio atrapaba cualquier excepción y
# devolvía f"Error: {str(e)}" tal cual al cliente -- filtraba SQL/rutas
# del servidor a la pantalla. Ahora lo que el servicio no sabe manejar
# sube, y backend/main.py responde un 500 genérico sin detalles.

from fastapi.testclient import TestClient

from backend.main import app
from services import pesaje_service


def test_error_no_manejado_no_filtra_detalle_interno(headers_romana, monkeypatch):
    # TestClient por defecto (raise_server_exceptions=True) vuelve a
    # lanzar en el propio test cualquier excepción no atrapada por un
    # handler -- es a propósito, para ver el traceback completo mientras
    # se desarrolla. Acá se quiere probar justamente el handler
    # (backend/main.py:_manejador_errores_no_previstos), así que se
    # necesita raise_server_exceptions=False en esta instancia puntual.
    client = TestClient(app, raise_server_exceptions=False)

    detalle_secreto = "detalle interno secreto: /ruta/del/servidor, tabla xyz, IP 10.0.0.5"

    def _explota(*args, **kwargs):
        raise RuntimeError(detalle_secreto)

    monkeypatch.setattr(pesaje_service, "registrar_entrada", _explota)

    r = client.post(
        "/api/v1/pesadas/entrada",
        json={"peso_bruto": 15000, "vehiculo_id": 1, "tipo_pesaje": "GENERAL"},
        headers=headers_romana,
    )

    assert r.status_code == 500
    assert detalle_secreto not in r.text
    assert "RuntimeError" not in r.text
    assert "Error interno del servidor" in r.json()["detail"]
