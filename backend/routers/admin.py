# ============================================================
# backend/routers/admin.py — Usuarios y configuración del sistema
# ============================================================
from fastapi import APIRouter, Depends, HTTPException, status
from starlette.concurrency import run_in_threadpool

from backend.deps import requiere_permiso, get_db
from backend.schemas.auth import UsuarioOut
from backend.schemas.admin import (
    UsuarioCrearIn, UsuarioPasswordIn, UsuarioActivoIn,
    ConfiguracionOut, ConfiguracionIn,
)
from database.engine import SessionLocal
from database.models import Configuracion
from services import auth_service

router = APIRouter(tags=["admin"])


@router.get("/usuarios", response_model=list[UsuarioOut], dependencies=[Depends(requiere_permiso("admin_usuarios"))])
async def listar_usuarios():
    return await run_in_threadpool(auth_service.listar_usuarios)


@router.post("/usuarios", dependencies=[Depends(requiere_permiso("admin_usuarios"))])
async def crear_usuario(body: UsuarioCrearIn):
    resultado = await run_in_threadpool(
        auth_service.crear_usuario, body.username, body.password, body.nombre_completo, body.nivel
    )
    if not resultado["exito"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=resultado["mensaje"])
    return {"mensaje": resultado["mensaje"]}


@router.post("/usuarios/{usuario_id}/password", dependencies=[Depends(requiere_permiso("admin_usuarios"))])
async def cambiar_password(usuario_id: int, body: UsuarioPasswordIn):
    resultado = await run_in_threadpool(auth_service.cambiar_password, usuario_id, body.nueva_password)
    if not resultado["exito"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=resultado["mensaje"])
    return {"mensaje": resultado["mensaje"]}


@router.patch("/usuarios/{usuario_id}/activo", dependencies=[Depends(requiere_permiso("admin_usuarios"))])
async def activar_desactivar_usuario(usuario_id: int, body: UsuarioActivoIn):
    resultado = await run_in_threadpool(auth_service.activar_desactivar_usuario, usuario_id, body.activo)
    if not resultado["exito"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=resultado["mensaje"])
    return {"mensaje": resultado["mensaje"]}


def _listar_configuracion_sync():
    db = SessionLocal()
    try:
        return db.query(Configuracion).order_by(Configuracion.clave).all()
    finally:
        db.close()


def _actualizar_configuracion_sync(clave: str, valor: str):
    db = SessionLocal()
    try:
        cfg = db.query(Configuracion).filter_by(clave=clave).first()
        if not cfg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Clave de configuración '{clave}' no encontrada")
        cfg.valor = valor
        db.commit()
        db.refresh(cfg)
        return cfg
    finally:
        db.close()


@router.get("/configuracion", response_model=list[ConfiguracionOut], dependencies=[Depends(requiere_permiso("admin_configuracion"))])
async def listar_configuracion():
    return await run_in_threadpool(_listar_configuracion_sync)


@router.put("/configuracion/{clave}", response_model=ConfiguracionOut, dependencies=[Depends(requiere_permiso("admin_configuracion"))])
async def actualizar_configuracion(clave: str, body: ConfiguracionIn):
    return await run_in_threadpool(_actualizar_configuracion_sync, clave, body.valor)
