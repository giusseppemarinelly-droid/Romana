# ============================================================
# backend/ws/manager.py — Broadcast de eventos en tiempo real
# ============================================================
# Notificación best-effort, NO fuente de verdad: si un cliente estaba
# desconectado se pierde el evento, pero al reconectar cada cliente
# vuelve a pedir su lista vía GET normal (ver client/ws_client.py y
# las vistas de gui/centro_costos y gui/pesaje). El WS solo dispara el
# refresco; el estado real siempre vive en Postgres.
#
# Limitación conocida (documentada para la tesis): el broadcast es en
# memoria del proceso — solo funciona corriendo un único worker de
# uvicorn (`--workers 1`). Escalar a múltiples workers requeriría un
# pub/sub externo (ej. Redis), fuera del alcance de este proyecto.

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, evento: dict):
        muertos = []
        for ws in self.active:
            try:
                await ws.send_json(evento)
            except Exception:
                muertos.append(ws)
        for ws in muertos:
            self.disconnect(ws)


manager = ConnectionManager()
