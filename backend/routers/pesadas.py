# ============================================================
# backend/routers/pesadas.py — Mapea 1:1 services/pesaje_service.py
# ============================================================
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.concurrency import run_in_threadpool

from backend.deps import get_current_user, requiere_permiso
from backend.schemas.pesada import (
    PesadaOut, EntradaIn, SalidaIn, RechazoIn, CompletarIn, AnularIn,
    CorteIn, CorteOut,
)
from backend.ws.manager import manager
from database.engine import SessionLocal
from database.models import Usuario, Pesada
from services import pesaje_service

router = APIRouter(prefix="/pesadas", tags=["pesadas"])


def _fallo_si_no_exito(resultado: dict):
    if not resultado["exito"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=resultado["mensaje"])


def _obtener_pesada_sync(pesada_id: int) -> Pesada:
    db = SessionLocal()
    try:
        pesada = db.query(Pesada).options(*pesaje_service._pesada_options()).filter_by(id=pesada_id).first()
        if not pesada:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pesada no encontrada")
        return pesada
    finally:
        db.close()


async def _obtener_pesada(pesada_id: int) -> Pesada:
    return await run_in_threadpool(_obtener_pesada_sync, pesada_id)


@router.post("/entrada", response_model=PesadaOut, dependencies=[Depends(requiere_permiso("pesaje_entrada"))])
async def registrar_entrada(body: EntradaIn, usuario: Usuario = Depends(get_current_user)):
    resultado = await run_in_threadpool(
        pesaje_service.registrar_entrada, **body.model_dump(), usuario_id=usuario.id
    )
    _fallo_si_no_exito(resultado)
    await manager.broadcast({"tipo": "pesada_creada", "pesada_id": resultado["pesada"].id})
    return resultado["pesada"]


@router.post("/{pesada_id}/salida", response_model=PesadaOut, dependencies=[Depends(requiere_permiso("pesaje_salida"))])
async def capturar_salida(pesada_id: int, body: SalidaIn, usuario: Usuario = Depends(get_current_user)):
    resultado = await run_in_threadpool(
        pesaje_service.capturar_peso_salida, pesada_id, body.peso_capturado, usuario_id=usuario.id
    )
    _fallo_si_no_exito(resultado)
    # Evento clave: dispara el refresco automático de la cola en Centro de Costos.
    await manager.broadcast({"tipo": "pesada_pendiente_aprobacion", "pesada_id": pesada_id})
    return resultado["pesada"]


@router.post("/{pesada_id}/aprobar", response_model=PesadaOut, dependencies=[Depends(requiere_permiso("centro_costos"))])
async def aprobar(pesada_id: int, usuario: Usuario = Depends(get_current_user)):
    resultado = await run_in_threadpool(pesaje_service.aprobar_pesada, pesada_id, usuario_id=usuario.id)
    _fallo_si_no_exito(resultado)
    # Evento clave: dispara el refresco automático en la estación de Romana.
    await manager.broadcast({"tipo": "pesada_aprobada", "pesada_id": pesada_id})
    return resultado["pesada"]


@router.post("/{pesada_id}/rechazar", response_model=PesadaOut, dependencies=[Depends(requiere_permiso("centro_costos"))])
async def rechazar(pesada_id: int, body: RechazoIn, usuario: Usuario = Depends(get_current_user)):
    resultado = await run_in_threadpool(
        pesaje_service.rechazar_pesada, pesada_id, body.motivo, usuario_id=usuario.id
    )
    _fallo_si_no_exito(resultado)
    await manager.broadcast({"tipo": "pesada_rechazada", "pesada_id": pesada_id})
    # rechazar_pesada() no recarga/devuelve la pesada (a diferencia de las demás
    # transiciones), así que se recarga explícitamente para responder consistente.
    return await _obtener_pesada(pesada_id)


@router.post("/{pesada_id}/completar", response_model=PesadaOut, dependencies=[Depends(requiere_permiso("pesaje_completar"))])
async def completar(pesada_id: int, body: CompletarIn, usuario: Usuario = Depends(get_current_user)):
    resultado = await run_in_threadpool(
        pesaje_service.completar_pesaje, pesada_id, **body.model_dump(), usuario_id=usuario.id
    )
    _fallo_si_no_exito(resultado)
    await manager.broadcast({"tipo": "pesada_completada", "pesada_id": pesada_id})
    return resultado["pesada"]


@router.post("/{pesada_id}/anular", dependencies=[Depends(requiere_permiso("pesaje_anular"))])
async def anular(pesada_id: int, body: AnularIn):
    resultado = await run_in_threadpool(pesaje_service.anular_pesada, pesada_id, body.motivo)
    _fallo_si_no_exito(resultado)
    await manager.broadcast({"tipo": "pesada_anulada", "pesada_id": pesada_id})
    return {"mensaje": resultado["mensaje"]}


@router.get("/en-planta", response_model=list[PesadaOut])
async def listar_en_planta():
    return await run_in_threadpool(pesaje_service.listar_pesadas_en_planta)


@router.get("/pendientes-aprobacion", response_model=list[PesadaOut], dependencies=[Depends(requiere_permiso("centro_costos"))])
async def listar_pendientes():
    return await run_in_threadpool(pesaje_service.listar_pendientes_aprobacion)


@router.get("/aprobadas-pendientes", response_model=list[PesadaOut])
async def listar_aprobadas_pendientes():
    return await run_in_threadpool(pesaje_service.listar_aprobadas_pendientes_completar)


@router.get("/completadas", response_model=list[PesadaOut])
async def listar_completadas(limit: int = 100):
    return await run_in_threadpool(pesaje_service.listar_pesadas_completadas, limit)


@router.get("/kardex/buscar", response_model=list[PesadaOut])
async def kardex(
    fecha_inicio: Optional[datetime] = None,
    fecha_fin: Optional[datetime] = None,
    producto_id: Optional[int] = None,
    proveedor_id: Optional[int] = None,
    vehiculo_id: Optional[int] = None,
    estado: Optional[str] = None,
    limit: int = 500,
):
    return await run_in_threadpool(
        pesaje_service.get_kardex,
        fecha_inicio, fecha_fin, producto_id, proveedor_id, vehiculo_id, estado, limit,
    )


@router.get("/vehiculo/{vehiculo_id}/activa", response_model=Optional[PesadaOut])
async def pesada_activa_por_vehiculo(vehiculo_id: int):
    return await run_in_threadpool(pesaje_service.get_pesada_en_planta_por_vehiculo, vehiculo_id)


@router.get("/{pesada_id}", response_model=PesadaOut)
async def obtener_pesada(pesada_id: int):
    return await _obtener_pesada(pesada_id)


@router.post("/cortes", response_model=CorteOut, dependencies=[Depends(requiere_permiso("corte_pesadas"))])
async def crear_corte(body: CorteIn, usuario: Usuario = Depends(get_current_user)):
    resultado = await run_in_threadpool(pesaje_service.realizar_corte, body.observaciones, usuario.id)
    _fallo_si_no_exito(resultado)
    return resultado["corte"]
