# ============================================================
# backend/routers/auth.py
# ============================================================
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.deps import get_db, get_current_user
from backend.security import crear_token
from backend.schemas.auth import LoginRequest, LoginResponse, UsuarioOut
from database.models import Usuario
from services.auth_service import verificar_credenciales

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    resultado = verificar_credenciales(db, body.username, body.password)
    if not resultado["exito"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=resultado["mensaje"])

    usuario = resultado["usuario"]
    return LoginResponse(
        access_token=crear_token(usuario),
        usuario=UsuarioOut.model_validate(usuario),
        nivel_nombre=resultado["nivel_nombre"],
    )


@router.get("/me", response_model=UsuarioOut)
def me(usuario: Usuario = Depends(get_current_user)):
    return usuario
