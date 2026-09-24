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
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from config import WEB_DIST_DIR
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


RUTA_WEB_SUPERVISION = "/supervision"


class _EstaticosWeb(StaticFiles):
    """
    StaticFiles con cabeceras de caché pensadas para un build de Vite.

    - HTML (index.html): `no-cache` -- el navegador lo revalida en cada
      visita. Sin esto, después de un `npm run build` seguía mostrando la
      versión vieja aunque el servidor ya sirviera la nueva.
    - assets/: el nombre lleva un hash del contenido (index-BT98wnq4.js),
      si el archivo cambia cambia el nombre, así que se cachean para
      siempre y no se vuelven a bajar en cada visita.
    """

    async def get_response(self, path, scope):
        respuesta = await super().get_response(path, scope)
        # En Windows Starlette entrega la ruta con "\\" (os.path.normpath).
        ruta = path.replace("\\", "/")
        if respuesta.media_type == "text/html" or ruta.endswith(".html") or ruta in ("", "."):
            respuesta.headers["Cache-Control"] = "no-cache"
        elif ruta.startswith("assets/") and respuesta.status_code == 200:
            respuesta.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return respuesta


def montar_web_supervision(app: FastAPI, directorio: str) -> bool:
    """
    Sirve la web de supervisión (web/dist, React compilado) desde este
    mismo proceso: un solo servidor y un solo puerto, sin hosting aparte
    (ver docs/SPEC-web-supervision.md). Mismo origen que la API, así que
    la web tampoco necesita CORS.

    Bajo /supervision y NO en "/", a propósito: montado en la raíz, el
    StaticFiles se queda con cualquier request que ninguna ruta de la API
    matchee del todo, y un GET a una ruta que solo acepta POST pasa de
    405 "Method Not Allowed" a 404 (comprobado con Starlette 0.41, ver
    backend/tests/test_web_supervision.py). Bajo un prefijo propio la API
    responde exactamente igual que antes.

    Si la web no está compilada (falta index.html) no monta nada y el
    backend arranca igual: las estaciones de pesaje dependen de este
    proceso, un frontend opcional sin compilar no puede tirarlo abajo.
    """
    if not os.path.isfile(os.path.join(directorio, "index.html")):
        print(f"Aviso - web de supervisión no compilada ({directorio}): no se sirve. "
              "Para servirla, correr `npm run build` en web/.")
        return False

    app.mount(RUTA_WEB_SUPERVISION, _EstaticosWeb(directory=directorio, html=True),
              name="web_supervision")

    # api_route con HEAD explícito: @app.get de FastAPI, a diferencia de
    # Starlette, no acepta HEAD solo -- un HEAD a la raíz daba 405.
    @app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
    def _raiz():
        return RedirectResponse(f"{RUTA_WEB_SUPERVISION}/")

    print(f"OK - Web de supervisión en {RUTA_WEB_SUPERVISION}/")
    return True


montar_web_supervision(app, WEB_DIST_DIR)
