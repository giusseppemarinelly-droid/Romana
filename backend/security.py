# ============================================================
# backend/security.py — Emisión y verificación de JWT
# ============================================================
# Los clientes (GUIs de Romana y Centro de Costos) son apps de
# escritorio, no navegadores: no hay cookies ni riesgo de CSRF/XSS
# que mitigar. Por eso se usa un token JWT enviado en el header
# "Authorization: Bearer <token>" en vez de sesiones con cookie.

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_MINUTES
from database.models import Usuario


def crear_token(usuario: Usuario) -> str:
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario.id),
        "username": usuario.username,
        "nivel": usuario.nivel,
        "iat": ahora,
        "exp": ahora + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decodificar_token(token: str) -> Optional[dict]:
    """Devuelve el payload si el token es válido, None si expiró o es inválido."""
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
