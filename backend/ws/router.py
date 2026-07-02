# ============================================================
# backend/ws/router.py — Endpoint /ws/pesadas
# ============================================================
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

from database.engine import SessionLocal
from database.models import Usuario
from backend.security import decodificar_token
from backend.ws.manager import manager

router = APIRouter(tags=["websocket"])


def _usuario_valido_desde_token(token: str) -> bool:
    payload = decodificar_token(token)
    if payload is None:
        return False
    db: Session = SessionLocal()
    try:
        usuario = db.query(Usuario).filter_by(id=int(payload["sub"])).first()
        return usuario is not None and usuario.activo
    finally:
        db.close()


@router.websocket("/ws/pesadas")
async def ws_pesadas(websocket: WebSocket, token: str = Query(...)):
    # El handshake de WebSocket no soporta headers custom de forma
    # sencilla desde clientes simples, por eso el JWT viaja como
    # query param en vez de en el header Authorization.
    if not _usuario_valido_desde_token(token):
        await websocket.close(code=4401)
        return

    await manager.connect(websocket)
    try:
        while True:
            # No esperamos mensajes del cliente; solo mantenemos la
            # conexión viva para recibir el broadcast del servidor.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
