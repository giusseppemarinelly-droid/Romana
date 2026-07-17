# ============================================================
# services/auth_service.py — Servicio de Autenticación
# ============================================================
# Este módulo maneja TODO lo relacionado con usuarios:
#   - Verificación de contraseñas
#   - Definición de permisos por nivel (PERMISOS es la fuente de verdad
#     que usan tanto backend/deps.py — autoridad real, servidor — como
#     client/api_client.py.tiene_permiso() — solo decide qué mostrar
#     en la GUI)
#   - Gestión de usuarios (alta, cambio de password, activar/desactivar)
#
# ¿Qué es un "servicio"?
#   Es la capa de LÓGICA DE NEGOCIO. No se mezcla con la GUI
#   ni con la base de datos directamente. Recibe datos, los
#   procesa y devuelve resultados.
#
# Nota histórica: este módulo tuvo alguna vez un singleton de proceso
# (`_usuario_actual`) que guardaba "quién está logueado" — un patrón
# válido para una app de escritorio de un solo usuario, pero incorrecto
# para un backend HTTP donde cada request puede ser de un usuario
# distinto. Se eliminó al terminar la migración a cliente-servidor;
# ahora "quién está logueado" vive en el JWT de cada request (backend)
# o en `client.api_client.api_client.usuario` (GUI).

import bcrypt
from datetime import datetime
from database.engine import SessionLocal
from database.models import Usuario


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
    "pesaje_ver_pendientes_cc": [1, 2, 3, 4], # Romana también puede VER la cola de
                                            # CC (solo lectura, en Completar Pesaje)
                                            # -- aprobar/rechazar sigue siendo solo CC

    # --- Centro de Costos ---
    "centro_costos":        [1, 2, 4],      # CC + admin pueden aprobar/rechazar

    # --- Maestros ---
    "maestros_ver":         [1, 2, 3],      # Romana ve los maestros
    "maestros_crear":       [1, 2],         # Admin y supervisor crean
    "maestros_editar":      [1, 2],         # Admin y supervisor editan
    "maestros_eliminar":    [1],            # Solo admin elimina

    # --- Reportes ---
    "reportes_ver":         [1, 2, 3],      # Romana ve reportes básicos
    "reportes_exportar":    [1, 2, 3],      # Romana también exporta (necesita el ticket/factura)

    # --- Administración ---
    "admin_usuarios":       [1],            # Solo admin gestiona usuarios
    "admin_configuracion":  [1],            # Solo admin configura el sistema
}


# ============================================================
# LOGIN
# ============================================================

def verificar_credenciales(db, username: str, password: str) -> dict:
    """
    Verifica usuario/contraseña contra la BD. La usa
    backend/routers/auth.py en cada request de login — es stateless,
    no guarda nada a nivel de proceso.

    Recibe una sesión `db` ya abierta (el llamador es responsable de
    cerrarla) para poder actualizar `last_login` sin abrir una segunda
    sesión.

    Returns:
        dict con "exito", "mensaje", "usuario" (objeto Usuario o None).
    """
    if not username or not password:
        return {"exito": False, "mensaje": "Usuario y contraseña son requeridos", "usuario": None}

    usuario = db.query(Usuario).filter(
        Usuario.username == username.strip().lower()
    ).first()

    if not usuario:
        return {"exito": False, "mensaje": "Usuario no encontrado", "usuario": None}

    if not usuario.activo:
        return {"exito": False, "mensaje": "Usuario desactivado. Contacte al administrador", "usuario": None}

    password_correcta = bcrypt.checkpw(
        password.encode("utf-8"),
        usuario.password_hash.encode("utf-8")
    )

    if not password_correcta:
        return {"exito": False, "mensaje": "Contraseña incorrecta", "usuario": None}

    usuario.last_login = datetime.now()
    db.commit()
    db.refresh(usuario)

    nivel_nombre = {1: "Administrador", 2: "Supervisor", 3: "Operador", 4: "Centro de Costos"}
    return {
        "exito": True,
        "mensaje": f"Bienvenido, {usuario.nombre_completo}",
        "usuario": usuario,
        "nivel_nombre": nivel_nombre.get(usuario.nivel, "Desconocido")
    }


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
