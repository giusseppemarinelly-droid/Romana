# ============================================================
# config.py — Configuración global del sistema
# ============================================================
# Este archivo centraliza TODAS las configuraciones del sistema.
# Si necesitas cambiar algo (nombre empresa, puerto COM, etc.)
# solo editas este archivo, no tienes que buscar en todo el código.

import os

# -------------------------------------------------------
# RUTAS Y CONEXIÓN A BASE DE DATOS
# -------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Configuración de PostgreSQL
# Formato: postgresql+pg8000://<usuario>:<contraseña>@<host>:<puerto>/<nombre_bd>
# Override vía ROMANA_DATABASE_URL — lo usa backend/tests/conftest.py para
# apuntar a una BD de pruebas aislada en vez de la BD real.
DATABASE_URL = os.environ.get(
    "ROMANA_DATABASE_URL",
    "postgresql+pg8000://postgres:postgres@localhost:5433/romana_db",
)

REPORTS_DIR = os.path.join(BASE_DIR, "reports", "output")
TEMPLATES_DIR = os.path.join(BASE_DIR, "reports", "templates")

# -------------------------------------------------------
# INFORMACIÓN DE LA EMPRESA
# -------------------------------------------------------
EMPRESA = {
    "nombre":    "MI EMPRESA, C.A.",
    "rif":       "J-000000000-0",
    "direccion": "Ciudad, Estado, País",
    "telefono":  "+58 000-000-0000",
    "email":     "info@miempresa.com",
    "logo":      os.path.join(TEMPLATES_DIR, "logo.png"),
}

# -------------------------------------------------------
# CONFIGURACIÓN DEL DISPLAY DE PESAJE (Toledo)
# -------------------------------------------------------
DISPLAY = {
    "marca":     "Simulador",
    "puerto":    "COM1",
    "baudrate":  9600,
    "timeout":   2,
    "bits_dato": 8,
    "paridad":   "N",
    "bits_stop": 1,
}

# -------------------------------------------------------
# CONFIGURACIÓN DE LA BÁSCULA
# -------------------------------------------------------
BASCULA = {
    "nombre":          "Báscula Principal",
    "capacidad_max":   80000,
    "capacidad_min":   200,
    "division":        20,
    "unidad":          "KG",
}

# -------------------------------------------------------
# CONFIGURACIÓN DE TICKETS
# -------------------------------------------------------
TICKET = {
    "prefijo":          "TK",
    "copias":           1,
    "formato_fecha":    "%d/%m/%Y %H:%M:%S",
}

# -------------------------------------------------------
# APARIENCIA DE LA INTERFAZ — Paleta Corporativa
# -------------------------------------------------------
UI = {
    "tema":               "light",

    # Colores de acento / acción principal — Azul corporativo
    "color_accent":       "#1d4ed8",   # Azul real corporativo (blue-700)
    "color_accent_hover": "#1e40af",   # Azul profundo al hacer hover (blue-800)

    # Fondos
    "color_bg":           "#f1f5f9",   # Fondo general ligeramente grisáceo (slate-100)
    "color_card":         "#ffffff",   # Tarjetas blancas puras

    # Textos
    "color_text":         "#1e293b",   # Texto principal (slate-800)
    "color_muted":        "#64748b",   # Texto secundario (slate-500)

    # Bordes
    "color_border":       "#e2e8f0",   # Borde sutil (slate-200)

    # Estados
    "color_success":       "#059669",  # Verde para completados (emerald-600)
    "color_success_hover": "#047857",
    "color_warning":       "#b45309",  # Ámbar oscuro para pendientes (amber-700)
    "color_danger":        "#dc2626",  # Rojo (red-600)
    "color_danger_hover":  "#b91c1c",

    # ── SIDEBAR ────────────────────────────────────
    # Azul navy oscuro original
    "color_sidebar":       "#0f172a",   # Slate-900 oscuro original
    "color_sidebar_text":  "#e2e8f0",   # Texto claro
    "color_sidebar_hover": "#1e293b",   # Hover slate-800
    "color_sidebar_active":"#1d4ed8",   # Ítem activo — azul corporativo
    "color_sidebar_section":"#60a5fa",  # Etiquetas de sección — azul claro legible sobre oscuro
    "color_sidebar_bottom": "#070e1c",  # Panel inferior ligeramente más oscuro

    # Tipografía
    "fuente":             "Segoe UI",
    "fuente_size":        12,
}

# -------------------------------------------------------
# CONFIGURACIÓN DEL BACKEND (API + WebSockets)
# -------------------------------------------------------
# JWT_SECRET_KEY: en producción debe venir de una variable de entorno,
# nunca quedar hardcodeada en el repo. Se deja un default solo para
# desarrollo local.
JWT_SECRET_KEY  = os.environ.get("ROMANA_JWT_SECRET", "dev-secret-cambiar-en-produccion")
JWT_ALGORITHM   = "HS256"
JWT_EXPIRE_MINUTES = 12 * 60   # 12 horas — cubre un turno de operador

API_HOST = os.environ.get("ROMANA_API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("ROMANA_API_PORT", "8000"))
API_BASE_URL = os.environ.get("ROMANA_API_URL", "http://localhost:8000")

# -------------------------------------------------------
# CREAR DIRECTORIOS SI NO EXISTEN
# -------------------------------------------------------
for directorio in [REPORTS_DIR, TEMPLATES_DIR]:
    os.makedirs(directorio, exist_ok=True)
