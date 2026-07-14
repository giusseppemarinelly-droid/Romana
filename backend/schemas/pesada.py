# ============================================================
# backend/schemas/pesada.py — DTOs de la tabla central `pesadas`
# ============================================================
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from backend.schemas.auth import UsuarioOut
from backend.schemas.maestros import (
    VehiculoOut, ConductorOut, ProductoOut, ProveedorOut,
    DestinoOut, LoteOut, RemolqueOut, ContenedorOut,
)


class PesadaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero_ticket: str
    estado: str
    tipo_pesaje: str

    fecha_entrada: Optional[datetime] = None
    fecha_captura: Optional[datetime] = None
    fecha_aprobacion: Optional[datetime] = None
    fecha_salida: Optional[datetime] = None

    peso_bruto: Optional[float] = None
    peso_tara: Optional[float] = None
    peso_neto: Optional[float] = None

    empresa_transportista: Optional[str] = None
    empresa_cliente_proveedor: Optional[str] = None
    cedula_conductor_libre: Optional[str] = None

    orden_compra: Optional[str] = None
    cantidad: Optional[float] = None
    precintos: Optional[str] = None
    observaciones: Optional[str] = None
    motivo_rechazo: Optional[str] = None
    motivo_anulacion: Optional[str] = None
    anulada: bool

    vehiculo: Optional[VehiculoOut] = None
    conductor: Optional[ConductorOut] = None
    producto: Optional[ProductoOut] = None
    proveedor: Optional[ProveedorOut] = None
    destino: Optional[DestinoOut] = None
    lote: Optional[LoteOut] = None
    remolque: Optional[RemolqueOut] = None
    contenedor: Optional[ContenedorOut] = None
    usuario_entrada: Optional[UsuarioOut] = None
    usuario_salida: Optional[UsuarioOut] = None
    aprobado_por: Optional[UsuarioOut] = None


class EntradaIn(BaseModel):
    peso_bruto: float
    vehiculo_id: int
    tipo_pesaje: str = "GENERAL"
    producto_id: Optional[int] = None
    empresa_transportista: str = ""
    empresa_cliente_proveedor: str = ""
    conductor_id: Optional[int] = None
    cedula_conductor_libre: str = ""
    proveedor_id: Optional[int] = None
    destino_id: Optional[int] = None
    lote_id: Optional[int] = None
    remolque_id: Optional[int] = None
    contenedor_id: Optional[int] = None
    observaciones: str = ""


class SalidaIn(BaseModel):
    peso_capturado: float


class RechazoIn(BaseModel):
    motivo: str


class CompletarIn(BaseModel):
    orden_compra: str = ""
    cantidad: Optional[float] = None
    precintos: str = ""
    observaciones: str = ""


class AnularIn(BaseModel):
    motivo: str


class CorteIn(BaseModel):
    observaciones: str = ""


class CorteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    numero_corte: int
    fecha_inicio: datetime
    fecha_fin: datetime
    total_pesadas: int
    total_neto_kg: float
    observaciones: Optional[str] = None


class EstadisticasOut(BaseModel):
    en_planta: int
    completadas_hoy: int
    neto_hoy_kg: float
    total_completadas: int
