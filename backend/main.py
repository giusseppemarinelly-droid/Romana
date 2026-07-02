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

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.engine import crear_tablas
from backend.routers import auth, pesadas, reportes, admin
from backend.routers.maestros import todos_los_routers as routers_maestros
from backend.ws.router import router as ws_router


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
