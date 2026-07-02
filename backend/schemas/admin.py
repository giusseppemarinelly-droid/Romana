from typing import Optional

from pydantic import BaseModel, ConfigDict


class UsuarioCrearIn(BaseModel):
    username: str
    password: str
    nombre_completo: str
    nivel: int


class UsuarioPasswordIn(BaseModel):
    nueva_password: str


class UsuarioActivoIn(BaseModel):
    activo: bool


class ConfiguracionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    clave: str
    valor: Optional[str] = None
    descripcion: Optional[str] = None


class ConfiguracionIn(BaseModel):
    valor: str
