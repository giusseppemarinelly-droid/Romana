# ============================================================
# run_server.py — Arranca el backend (API + WebSockets)
# ============================================================
# Uso: python run_server.py
#
# Corre en la máquina "servidor" de la red interna de la planta.
# Las dos estaciones físicas (Romana y Centro de Costos) siguen
# arrancando con `python main.py` como siempre, apuntando a este
# servidor vía config.API_BASE_URL.

import uvicorn
from config import API_HOST, API_PORT

if __name__ == "__main__":
    # workers=1: ver nota en backend/ws/manager.py sobre por qué el
    # broadcast de WebSocket no soporta múltiples workers sin Redis.
    uvicorn.run("backend.main:app", host=API_HOST, port=API_PORT, workers=1, reload=False)
