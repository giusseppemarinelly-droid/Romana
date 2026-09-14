# ============================================================
# backend/main.py — Punto de entrada del backend (API + WebSockets)
# ============================================================
# Se ejecuta con: python run_server.py  (o `uvicorn backend.main:app`)
#
# Corre en la máquina que hace de "servidor": ambas estaciones físicas
# (Romana y Centro de Costos) le apuntan por red vía config.API_BASE_URL.
#
# IMPORTANTE (documentado también en ws/manager.py): correr con un solo
# worker (`uvicorn ... --workers 1`). El broadcast de WebSocket vive en
# memoria de un único proceso; con múltiples workers cada uno tendría
# su propia lista de conexiones y los eventos no llegarían a todos los
# clientes.

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database.engine import crear_tablas
from backend.routers import auth, pesadas, reportes, admin
from backend.routers.maestros import todos_los_routers as routers_maestros
from backend.ws.router import router as ws_router

logger = logging.getLogger("romana.backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    crear_tablas()
    yield


app = FastAPI(title="Romana API", version="1.0.0", lifespan=lifespan)

# CORS abierto: los clientes son apps de escritorio (customtkinter),
# no páginas web servidas desde un origen distinto — no hay navegador
# de por medio que necesite esta protección. Se deja permisivo para no
# bloquear el desarrollo local en distintas máquinas de la red interna.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def _manejador_errores_no_previstos(request: Request, exc: Exception):
    """
    Hallazgo I-10: antes, cada función de services/pesaje_service.py
    devolvía f"Error: {str(e)}" tal cual, y la GUI lo mostraba en un
    messagebox sin filtrar -- eso exponía fragmentos de SQL y rutas del
    servidor en pantalla, y enmascaraba bugs de programación reales como
    si fueran errores de negocio esperados (un AttributeError y "el
    vehículo ya tiene pesada activa" llegaban por el mismo canal,
    indistinguibles). Los servicios ahora dejan subir lo que no saben
    manejar en vez de atraparlo genérico -- este handler es donde
    termina esa excepción: se loguea el traceback completo del lado del
    servidor (para poder diagnosticarla de verdad) y se responde al
    cliente un mensaje genérico, sin detalles internos. No interfiere
    con HTTPException (401/400/404, etc.) -- Starlette las sigue
    resolviendo con su propio handler más específico, este solo agarra
    lo que nadie más atrapó.
    """
    logger.exception(f"Error no manejado en {request.method} {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor. Contacte al administrador si el problema persiste."},
    )


app.include_router(auth.router, prefix="/api/v1")
app.include_router(pesadas.router, prefix="/api/v1")
app.include_router(reportes.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
for r in routers_maestros:
    app.include_router(r, prefix="/api/v1")
app.include_router(ws_router)


@app.get("/health")
def health():
    return {"status": "ok"}
