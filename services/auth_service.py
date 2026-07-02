# ============================================================
# services/auth_service.py — Servicio de Autenticación
# ============================================================
# Este módulo maneja TODO lo relacionado con usuarios:
#   - Login y logout
#   - Verificación de contraseñas
#   - Control de permisos por nivel
#   - Sesión activa del usuario
#
# ¿Qué es un "servicio"?
#   Es la capa de LÓGICA DE NEGOCIO. No se mezcla con la GUI
#   ni con la base de datos directamente. Recibe datos, los
#   procesa y devuelve resultados.

import bcrypt
from datetime import datetime
from typing import Optional
from database.engine import SessionLocal
from database.models import Usuario


# ============================================================
# SESIÓN ACTIVA
# ============================================================
# Variable global que guarda el usuario que está logueado.
# Es None cuando nadie está logueado.
_usuario_actual: Optional[Usuario] = None


def get_usuario_actual() -> Optional[Usuario]:
    """Devuelve el usuario que está actualmente logueado."""
    return _usuario_actual


def get_nivel_actual() -> int:
    """Devuelve el nivel del usuario logueado (0 si nadie está logueado)."""
    if _usuario_actual:
        return _usuario_actual.nivel
    return 0


# ============================================================
# PERMISOS POR NIVEL
# ============================================================
# Diccionario que define qué puede hacer cada nivel.
# True = puede hacerlo, False = no puede.
PERMISOS = {
    # --- Pesajes (Romana) ---
    "pesaje_entrada":       [1, 2, 3],      # Romana hace entradas
    "pesaje_salida":        [1, 2, 3],      # Romana captura 2° peso
    "pesaje_completar":     [1, 2, 3],      # Romana completa post-aprobación
    "pesaje_anular":        [1, 2],         # Solo admin y supervisor anulan
    "corte_pesadas":        [1, 2],         # Solo admin y supervisor hacen cortes

    # --- Centro de Costos ---
    "centro_costos":        [1, 2, 4],      # CC + admin pueden aprobar/rechazar

    # --- Maestros ---
    "maestros_ver":         [1, 2, 3],      # Romana ve los maestros
    "maestros_crear":       [1, 2],         # Admin y supervisor crean
    "maestros_editar":      [1, 2],         # Admin y supervisor editan
    "maestros_eliminar":    [1],            # Solo admin elimina

    # --- Reportes ---
    "reportes_ver":         [1, 2, 3],      # Romana ve reportes básicos
    "reportes_exportar":    [1, 2],         # Admin y supervisor exportan

    # --- Administración ---
    "admin_usuarios":       [1],            # Solo admin gestiona usuarios
    "admin_configuracion":  [1],            # Solo admin configura el sistema
}


def tiene_permiso(accion: str) -> bool:
    """
    Verifica si el usuario logueado tiene permiso para una acción.

    Uso:
        if tiene_permiso("pesaje_anular"):
            # mostrar botón de anulación
        else:
            # ocultar el botón

    Args:
        accion: Nombre de la acción (debe estar en el dict PERMISOS)

    Returns:
        True si el usuario tiene permiso, False si no.
    """
    if _usuario_actual is None:
        return False  # Si no hay nadie logueado, ningún permiso

    niveles_permitidos = PERMISOS.get(accion, [])
    return _usuario_actual.nivel in niveles_permitidos


# ============================================================
# LOGIN / LOGOUT
# ============================================================

def login(username: str, password: str) -> dict:
    """
    Intenta autenticar a un usuario con su usuario y contraseña.

    Args:
        username: Nombre de usuario
        password: Contraseña en texto plano

    Returns:
        dict con:
          - "exito": True/False
          - "mensaje": Mensaje descriptivo
          - "usuario": Objeto Usuario si exitoso, None si falló
    """
    global _usuario_actual

    if not username or not password:
        return {"exito": False, "mensaje": "Usuario y contraseña son requeridos", "usuario": None}

    db = SessionLocal()
    try:
        # Buscar usuario en la base de datos
        usuario = db.query(Usuario).filter(
            Usuario.username == username.strip().lower()
        ).first()

        # ¿Existe el usuario?
        if not usuario:
            return {"exito": False, "mensaje": "Usuario no encontrado", "usuario": None}

        # ¿Está activo?
        if not usuario.activo:
            return {"exito": False, "mensaje": "Usuario desactivado. Contacte al administrador", "usuario": None}

        # ¿La contraseña es correcta?
        password_correcta = bcrypt.checkpw(
            password.encode("utf-8"),
            usuario.password_hash.encode("utf-8")
        )

        if not password_correcta:
            return {"exito": False, "mensaje": "Contraseña incorrecta", "usuario": None}

        # ✅ Login exitoso
        usuario.last_login = datetime.now()
        db.commit()
        db.refresh(usuario)

        # Guardar en sesión global
        _usuario_actual = usuario

        nivel_nombre = {1: "Administrador", 2: "Supervisor", 3: "Operador"}
        return {
            "exito": True,
            "mensaje": f"Bienvenido, {usuario.nombre_completo}",
            "usuario": usuario,
            "nivel_nombre": nivel_nombre.get(usuario.nivel, "Desconocido")
        }

    except Exception as e:
        return {"exito": False, "mensaje": f"Error de sistema: {str(e)}", "usuario": None}
    finally:
        db.close()


def logout():
    """Cierra la sesión del usuario actual."""
    global _usuario_actual
    _usuario_actual = None


# ============================================================
# GESTIÓN DE USUARIOS (solo para administradores)
# ============================================================

def crear_usuario(username: str, password: str, nombre_completo: str, nivel: int) -> dict:
    """
    Crea un nuevo usuario en el sistema.
    Solo debe llamarse si el usuario logueado tiene permiso "admin_usuarios".
    """
    db = SessionLocal()
    try:
        # Verificar que el username no exista
        if db.query(Usuario).filter_by(username=username.strip().lower()).first():
            return {"exito": False, "mensaje": f"El usuario '{username}' ya existe"}

        # Crear el nuevo usuario
        nuevo = Usuario(
            username=username.strip().lower(),
            password_hash=bcrypt.hashpw(
                password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8"),
            nombre_completo=nombre_completo,
            nivel=nivel,
            activo=True,
            created_at=datetime.now()
        )
        db.add(nuevo)
        db.commit()
        return {"exito": True, "mensaje": f"Usuario '{username}' creado exitosamente"}

    except Exception as e:
        db.rollback()
        return {"exito": False, "mensaje": f"Error: {str(e)}"}
    finally:
        db.close()


def cambiar_password(usuario_id: int, nueva_password: str) -> dict:
    """Cambia la contraseña de un usuario."""
    db = SessionLocal()
    try:
        usuario = db.query(Usuario).filter_by(id=usuario_id).first()
        if not usuario:
            return {"exito": False, "mensaje": "Usuario no encontrado"}

        usuario.password_hash = bcrypt.hashpw(
            nueva_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        db.commit()
        return {"exito": True, "mensaje": "Contraseña actualizada exitosamente"}
    except Exception as e:
        db.rollback()
        return {"exito": False, "mensaje": f"Error: {str(e)}"}
    finally:
        db.close()


def listar_usuarios() -> list:
    """Retorna todos los usuarios del sistema."""
    db = SessionLocal()
    try:
        return db.query(Usuario).order_by(Usuario.nivel, Usuario.username).all()
    finally:
        db.close()


def activar_desactivar_usuario(usuario_id: int, activo: bool) -> dict:
    """Activa o desactiva un usuario."""
    db = SessionLocal()
    try:
        usuario = db.query(Usuario).filter_by(id=usuario_id).first()
        if not usuario:
            return {"exito": False, "mensaje": "Usuario no encontrado"}
        if usuario.username == "admin" and not activo:
            return {"exito": False, "mensaje": "No se puede desactivar el administrador principal"}

        usuario.activo = activo
        db.commit()
        estado = "activado" if activo else "desactivado"
        return {"exito": True, "mensaje": f"Usuario {estado} exitosamente"}
    except Exception as e:
        db.rollback()
        return {"exito": False, "mensaje": f"Error: {str(e)}"}
    finally:
        db.close()
