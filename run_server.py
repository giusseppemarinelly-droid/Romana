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
from config import API_HOST, API_PORT, JWT_SECRET_KEY

_JWT_SECRET_DEV = "dev-secret-cambiar-en-produccion"


def _advertir_si_secreto_por_defecto():
    # Hallazgo I-08 de la auditoría: si ROMANA_JWT_SECRET no está exportado
    # y el backend escucha en una IP que no es solo local, cualquiera que
    # lea el repositorio puede forjar un token de Administrador. No se
    # aborta el arranque (rompería el uso normal en desarrollo/pruebas de
    # escritorio, donde API_HOST también suele quedar en 0.0.0.0) -- solo
    # se avisa fuerte en consola. Antes de exponer el backend a la red real
    # de planta, exportar ROMANA_JWT_SECRET es obligatorio, no opcional.
    if JWT_SECRET_KEY == _JWT_SECRET_DEV and API_HOST not in ("127.0.0.1", "localhost"):
        print("!" * 70)
        print("! ADVERTENCIA DE SEGURIDAD: ROMANA_JWT_SECRET no está configurado.")
        print(f"! El backend está usando el secreto de desarrollo y escuchando en")
        print(f"! {API_HOST} (no solo local). Cualquiera en la red puede forjar un")
        print("! token de Administrador. Exportar ROMANA_JWT_SECRET antes de usar")
        print("! esto contra la red real de planta.")
        print("!" * 70)


if __name__ == "__main__":
    _advertir_si_secreto_por_defecto()
    # workers=1: ver nota en backend/ws/manager.py sobre por qué el
    # broadcast de WebSocket no soporta múltiples workers sin Redis.
    uvicorn.run("backend.main:app", host=API_HOST, port=API_PORT, workers=1, reload=False)
