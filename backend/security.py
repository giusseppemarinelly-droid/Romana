# ============================================================
# backend/security.py — Emisión y verificación de JWT
# ============================================================
# Los clientes (GUIs de Romana y Centro de Costos) son apps de
# escritorio, no navegadores: no hay cookies ni riesgo de CSRF/XSS
# que mitigar. Por eso se usa un token JWT enviado en el header
# "Authorization: Bearer <token>" en vez de sesiones con cookie.

from datetime import datetime, timedelta, timezone
from ipaddress import ip_address
from typing import Optional

import jwt

from config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_MINUTES
from database.models import Usuario

# Mismo valor que el default de config.JWT_SECRET_KEY. Se repite acá a
# propósito: si alguien cambia el default de config.py sin pensar en esto, el
# chequeo de abajo deja de reconocerlo y hay que actualizarlo conscientemente.
_SECRETO_DE_DESARROLLO = "dev-secret-cambiar-en-produccion"


def _es_loopback(host: str) -> bool:
    if host in ("localhost", ""):
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


def verificar_secreto_de_produccion(api_host: str) -> None:
    """
    Aborta el arranque si el backend va a escuchar en una interfaz de red con
    el secreto JWT de desarrollo -- que está escrito en el repositorio, así que
    cualquiera que lo lea puede firmarse un token de nivel 1 (Administrador).

    Solo se permite ese secreto atado a loopback, donde el único cliente
    posible es la GUI de esta misma máquina (ver `_asegurar_backend()` en
    main.py, que arranca el backend de desarrollo justamente así).

    Falla al arrancar en vez de advertir: un servidor que no levanta se nota
    en el momento, uno que levanta inseguro no se nota nunca.
    """
    if JWT_SECRET_KEY != _SECRETO_DE_DESARROLLO or _es_loopback(api_host):
        return

    raise RuntimeError(
        "\n"
        "  El backend iba a escuchar en " + api_host + " con el secreto JWT de\n"
        "  desarrollo, que está publicado en el repositorio. Cualquiera en la red\n"
        "  podría firmarse un token de Administrador.\n\n"
        "  Generá uno y exportalo antes de arrancar:\n\n"
        '    python -c "import secrets; print(secrets.token_urlsafe(48))"\n'
        "    set ROMANA_JWT_SECRET=<el valor generado>        (Windows)\n"
        "    export ROMANA_JWT_SECRET=<el valor generado>     (Linux)\n\n"
        "  Para desarrollo en una sola máquina, atalo a loopback:\n"
        "    set ROMANA_API_HOST=127.0.0.1\n"
    )


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
