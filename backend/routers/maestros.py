# ============================================================
# backend/routers/maestros.py — CRUD + búsqueda indexada
# ============================================================
# Resuelve dos cuellos de botella de Bigsoft a la vez:
#   1. Los módulos de gui/maestros/ hoy saltan la capa de servicios
#      y acceden a SessionLocal directo — acá se centraliza el acceso.
#   2. El buscador de conductores/vehículos hoy carga TODA la tabla en
#      memoria y filtra client-side — acá se reemplaza por `ILIKE`
#      indexado en Postgres (ver migración Alembic para el índice
#      pg_trgm sobre placa/documento).
#
# Los catálogos maestros (vehículos, conductores, proveedores, empresas
# transportistas, productos, destinos) comparten el mismo patrón CRUD
# (listar+buscar, obtener, crear, editar, activar/desactivar), así que
# se generan con una única factory en vez de repetir el código N veces.

from typing import Optional, Type

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from backend.deps import requiere_permiso
from backend.schemas.maestros import (
    VehiculoOut, VehiculoIn,
    ConductorOut, ConductorIn,
    ProveedorOut, ProveedorIn,
    EmpresaTransportistaOut, EmpresaTransportistaIn,
    ProductoOut, ProductoIn,
    DestinoOut, DestinoIn,
    ActivoIn,
)
from database.engine import SessionLocal
from database.models import (
    Vehiculo, Conductor, Proveedor, EmpresaTransportista, Producto, Destino
)


def crear_router_maestro(
    *,
    prefix: str,
    tag: str,
    modelo,
    schema_out: Type[BaseModel],
    schema_in: Type[BaseModel],
    columnas_busqueda: list[str],
    orden_por: str,
) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[tag])

    def _sync(fn, *args):
        db = SessionLocal()
        try:
            return fn(db, *args)
        finally:
            db.close()

    def _listar(db, search: Optional[str], activo: Optional[bool]):
        query = db.query(modelo)
        if activo is not None:
            query = query.filter(modelo.activo == activo)
        if search:
            filtros = [getattr(modelo, col).ilike(f"%{search}%") for col in columnas_busqueda]
            query = query.filter(or_(*filtros))
        return query.order_by(getattr(modelo, orden_por)).all()

    def _obtener(db, item_id: int):
        item = db.query(modelo).filter_by(id=item_id).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{tag[:-1].capitalize()} no encontrado")
        return item

    def _crear(db, body: BaseModel):
        item = modelo(**body.model_dump())
        db.add(item)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe un registro con esos datos únicos (código/placa/documento)")
        db.refresh(item)
        return item

    def _editar(db, item_id: int, body: BaseModel):
        item = _obtener(db, item_id)
        for campo, valor in body.model_dump().items():
            setattr(item, campo, valor)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe un registro con esos datos únicos (código/placa/documento)")
        db.refresh(item)
        return item

    def _toggle_activo(db, item_id: int, activo: bool):
        item = _obtener(db, item_id)
        item.activo = activo
        db.commit()
        db.refresh(item)
        return item

    @router.get("", response_model=list[schema_out], dependencies=[Depends(requiere_permiso("maestros_ver"))])
    async def listar(search: Optional[str] = None, activo: Optional[bool] = True):
        return await run_in_threadpool(_sync, _listar, search, activo)

    @router.get("/{item_id}", response_model=schema_out, dependencies=[Depends(requiere_permiso("maestros_ver"))])
    async def obtener(item_id: int):
        return await run_in_threadpool(_sync, _obtener, item_id)

    @router.post("", response_model=schema_out, status_code=status.HTTP_201_CREATED, dependencies=[Depends(requiere_permiso("maestros_crear"))])
    async def crear(body: schema_in):
        return await run_in_threadpool(_sync, _crear, body)

    @router.put("/{item_id}", response_model=schema_out, dependencies=[Depends(requiere_permiso("maestros_editar"))])
    async def editar(item_id: int, body: schema_in):
        return await run_in_threadpool(_sync, _editar, item_id, body)

    @router.patch("/{item_id}/activo", response_model=schema_out, dependencies=[Depends(requiere_permiso("maestros_eliminar"))])
    async def toggle_activo(item_id: int, body: ActivoIn):
        return await run_in_threadpool(_sync, _toggle_activo, item_id, body.activo)

    return router


router_vehiculos = crear_router_maestro(
    prefix="/vehiculos", tag="vehiculos", modelo=Vehiculo,
    schema_out=VehiculoOut, schema_in=VehiculoIn,
    columnas_busqueda=["placa", "descripcion"], orden_por="placa",
)


def _autoregistrar_vehiculo_sync(body: VehiculoIn) -> Vehiculo:
    db = SessionLocal()
    try:
        item = Vehiculo(**body.model_dump())
        db.add(item)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe un vehículo con esa placa")
        db.refresh(item)
        return item
    finally:
        db.close()


@router_vehiculos.post(
    "/autoregistro", response_model=VehiculoOut, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(requiere_permiso("pesaje_entrada"))],
)
async def autoregistrar_vehiculo(body: VehiculoIn):
    """
    Registro rápido de un vehículo no catalogado al momento de pesar.

    A diferencia de POST /vehiculos (requiere "maestros_crear", solo
    niveles 1-2), esto lo puede hacer cualquiera con permiso de
    "pesaje_entrada" (niveles 1-3) — es exactamente el caso de uso que
    tenía la GUI antes de la migración: el operador de Romana no puede
    quedar bloqueado esperando a un supervisor solo porque un camión
    todavía no está en el catálogo de vehículos.
    """
    return await run_in_threadpool(_autoregistrar_vehiculo_sync, body)


router_conductores = crear_router_maestro(
    prefix="/conductores", tag="conductores", modelo=Conductor,
    schema_out=ConductorOut, schema_in=ConductorIn,
    columnas_busqueda=["nombre", "documento"], orden_por="nombre",
)

router_proveedores = crear_router_maestro(
    prefix="/proveedores", tag="proveedores", modelo=Proveedor,
    schema_out=ProveedorOut, schema_in=ProveedorIn,
    columnas_busqueda=["nombre", "codigo"], orden_por="nombre",
)

router_empresas_transportistas = crear_router_maestro(
    prefix="/empresas_transportistas", tag="empresas_transportistas", modelo=EmpresaTransportista,
    schema_out=EmpresaTransportistaOut, schema_in=EmpresaTransportistaIn,
    columnas_busqueda=["nombre", "codigo"], orden_por="nombre",
)

router_productos = crear_router_maestro(
    prefix="/productos", tag="productos", modelo=Producto,
    schema_out=ProductoOut, schema_in=ProductoIn,
    columnas_busqueda=["nombre", "codigo"], orden_por="nombre",
)

router_destinos = crear_router_maestro(
    prefix="/destinos", tag="destinos", modelo=Destino,
    schema_out=DestinoOut, schema_in=DestinoIn,
    columnas_busqueda=["nombre", "codigo"], orden_por="nombre",
)

todos_los_routers = [
    router_vehiculos, router_conductores, router_proveedores,
    router_empresas_transportistas, router_productos, router_destinos,
]
