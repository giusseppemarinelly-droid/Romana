from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# Hallazgo I-09: antes se aceptaba una contraseña de un solo carácter --
# min_length acá es la validación real (a nivel de schema, antes de
# tocar la base de datos), no una sugerencia de la UI.
_LONGITUD_MIN_PASSWORD = 6


class UsuarioCrearIn(BaseModel):
    username: str
    password: str = Field(min_length=_LONGITUD_MIN_PASSWORD)
    nombre_completo: str
    nivel: int


class UsuarioPasswordIn(BaseModel):
    nueva_password: str = Field(min_length=_LONGITUD_MIN_PASSWORD)


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
