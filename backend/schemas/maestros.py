# ============================================================
# backend/schemas/maestros.py — DTOs de catálogos maestros
# ============================================================
from typing import Optional

from pydantic import BaseModel, ConfigDict


class VehiculoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    placa: str
    descripcion: Optional[str] = None
    tara_registrada: Optional[float] = None
    tipo: Optional[str] = None
    proveedor_id: Optional[int] = None
    activo: bool


class VehiculoIn(BaseModel):
    placa: str
    descripcion: Optional[str] = None
    tara_registrada: Optional[float] = 0
    tipo: Optional[str] = "camion"
    proveedor_id: Optional[int] = None


class ConductorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    documento: str
    tipo_documento: Optional[str] = None
    telefono: Optional[str] = None
    activo: bool


class ConductorIn(BaseModel):
    nombre: str
    documento: str
    tipo_documento: Optional[str] = "cedula"
    telefono: Optional[str] = None


class ProveedorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    codigo: str
    nombre: str
    rif: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    activo: bool


class ProveedorIn(BaseModel):
    codigo: str
    nombre: str
    rif: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None


class ProductoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    codigo: str
    nombre: str
    unidad: Optional[str] = None
    tipo_pesaje: str
    descripcion: Optional[str] = None
    activo: bool


class ProductoIn(BaseModel):
    codigo: str
    nombre: str
    unidad: Optional[str] = "KG"
    tipo_pesaje: str = "GENERAL"
    descripcion: Optional[str] = None


class DestinoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
    activo: bool


class DestinoIn(BaseModel):
    codigo: str
    nombre: str
    descripcion: Optional[str] = None


class ActivoIn(BaseModel):
    activo: bool


class LoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    codigo: str
    producto_id: int
    proveedor_id: Optional[int] = None
    descripcion: Optional[str] = None
    activo: bool


class RemolqueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    placa: str
    descripcion: Optional[str] = None
    tara_registrada: Optional[float] = None
    activo: bool


class ContenedorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    codigo: str
    descripcion: Optional[str] = None
    tara: Optional[float] = None
    activo: bool
