# ============================================================
# backend/deps.py — Dependencies compartidas de FastAPI
# ============================================================
from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database.engine import SessionLocal
from database.models import Usuario
from services.auth_service import PERMISOS
from backend.security import decodificar_token

# tokenUrl es solo informativo (para /docs); el login real recibe JSON, no form-data.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    credenciales_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o expiradas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credenciales_invalidas

    payload = decodificar_token(token)
    if payload is None:
        raise credenciales_invalidas

    usuario = db.query(Usuario).filter_by(id=int(payload["sub"])).first()
    if usuario is None or not usuario.activo:
        raise credenciales_invalidas

    return usuario


def requiere_permiso(accion: str):
    """
    Factory de dependency que reemplaza los checks manuales de
    `services.auth_service.tiene_permiso()` que hacía la GUI.
    Reusa el mismo diccionario PERMISOS para no duplicar las reglas
    de negocio de quién puede hacer qué.
    """
    def checker(usuario: Usuario = Depends(get_current_user)) -> Usuario:
        niveles_permitidos = PERMISOS.get(accion, [])
        if usuario.nivel not in niveles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"El nivel {usuario.nivel} no tiene permiso para '{accion}'",
            )
        return usuario
    return checker
