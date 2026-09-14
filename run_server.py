# ============================================================
# run_server.py — Arranca el backend (API + WebSockets)
# ============================================================
# Uso: python run_server.py
#
# Corre en la máquina "servidor" de la red interna de la planta.
# Las dos estaciones físicas (Romana y Centro de Costos) siguen
# arrancando con `python main.py` como siempre, apuntando a este
# servidor vía config.API_BASE_URL.

import sys

import uvicorn
from config import API_HOST, API_PORT, JWT_SECRET_KEY

_JWT_SECRET_DEV = "dev-secret-cambiar-en-produccion"


def _fallar_si_secreto_por_defecto():
    # Hallazgo I-08 de la auditoría: si ROMANA_JWT_SECRET no está exportado
    # y el backend escucha en una IP que no es solo local, cualquiera que
    # lea el repositorio puede forjar un token de Administrador. Primero
    # se dejó como advertencia (no se quería tumbar el backend usado en
    # medio de pruebas de campo) -- completado ahora a fail-fast de
    # verdad, que es el remedio real: un sistema que no arranca es
    # infinitamente mejor que uno que arranca inseguro en silencio.
    #
    # Para desarrollo/pruebas puramente locales en una sola máquina, dos
    # salidas -- cualquiera de las dos alcanza, no hace falta las dos:
    #   1. export ROMANA_JWT_SECRET=<algo propio>
    #   2. export ROMANA_API_HOST=127.0.0.1  (nadie más en la red puede
    #      alcanzar el backend igual, así que no importa qué secreto use)
    if JWT_SECRET_KEY == _JWT_SECRET_DEV and API_HOST not in ("127.0.0.1", "localhost"):
        print("!" * 70)
        print("! ARRANQUE ABORTADO: ROMANA_JWT_SECRET no está configurado.")
        print(f"! El backend intentaría escuchar en {API_HOST} (no solo local) usando")
        print("! el secreto JWT de desarrollo -- cualquiera en la red podría forjar")
        print("! un token de Administrador con solo leer el código fuente.")
        print("!")
        print("! Arreglar con UNA de estas dos (no hacen falta las dos):")
        print("!   export ROMANA_JWT_SECRET=<un secreto propio, no compartido>")
        print("!   export ROMANA_API_HOST=127.0.0.1   (si esto es solo para probar")
        print("!                                        en esta misma máquina)")
        print("!" * 70)
        sys.exit(1)


if __name__ == "__main__":
    _fallar_si_secreto_por_defecto()
    # workers=1: ver nota en backend/ws/manager.py sobre por qué el
    # broadcast de WebSocket no soporta múltiples workers sin Redis.
    uvicorn.run("backend.main:app", host=API_HOST, port=API_PORT, workers=1, reload=False)
