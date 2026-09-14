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
# Datos de Sura de Venezuela, C.A. (Planta Guacara) -- de sura.com.ve
# (nombre, dirección, teléfono, email) cruzado con directorios de
# empresas (pymesvenezuela.com) para el RIF. El RIF en particular NO
# está publicado en el sitio oficial de la empresa, solo en un
# directorio de terceros -- confirmarlo contra un documento real (RIF
# físico, una factura) antes de imprimir tickets de producción con él.
EMPRESA = {
    "nombre":    "SURA DE VENEZUELA, C.A.",
    "rif":       "J-30622535-8",  # TODO: confirmar contra el RIF físico -- fuente es un directorio de terceros, no SENIAT
    "direccion": "Zona Industrial Pruinca, Calle 1, Parcela 4, Guacara, Edo. Carabobo, Venezuela",
    "telefono":  "+58 241 300.1900",
    "email":     "atencionalcliente@sura.com.ve",
    "logo":      os.path.join(TEMPLATES_DIR, "logo.png"),
}

# -------------------------------------------------------
# CONFIGURACIÓN DEL DISPLAY DE PESAJE (Toledo)
# -------------------------------------------------------
# "AUTO": escanea todos los puertos COM disponibles y usa el primero que
# responda con una trama Toledo real (ver hardware/display_toledo.py,
# detectar_puerto_toledo()) -- pensado para la tarjeta multipuerto de la
# estación Romana (WCH PCI Express-SERIAL, hasta 4 puertos COM de una
# sola tarjeta, ver CLAUDE.md), donde Windows puede reasignar el número
# de puerto (reinstalación, driver nuevo, otro slot). El puerto ya
# confirmado en sitio es COM2, pero no hace falta fijarlo a mano.
# Override vía ROMANA_DISPLAY_PUERTO -- para forzar un puerto puntual en
# vez de escanear (ej. si hay más de un dispositivo serial y se quiere
# ser explícito) sin tocar este archivo.
DISPLAY = {
    "marca":     "Toledo",
    "puerto":    os.environ.get("ROMANA_DISPLAY_PUERTO", "AUTO"),
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

    # Campos de entrada (entries, comboboxes) — fondo levemente
    # distinto de las tarjetas para que se noten como "editables"
    "color_input_bg":      "#f8fafc",  # Slate-50

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
# "127.0.0.1", NO "localhost": confirmado en pruebas de campo 2026-09-12
# que resolver "localhost" en esta red le agrega ~2 SEGUNDOS a cada
# request -- Windows intenta conectar primero por IPv6 (::1), el
# backend solo escucha IPv4 (API_HOST=0.0.0.0), y el intento por IPv6
# tarda ~2s en fallar antes de caer a IPv4. Con la IP explícita se salta
# ese intento por completo (0.25s vs 2.3s, medido). Como client/
# api_client.py usa esta URL base para TODAS las llamadas al backend, el
# impuesto de 2s pegaba en cada pantalla y cada login -- era el motivo
# real detrás de "el sistema se queda colgado", no algo del código de
# cada pantalla.
API_BASE_URL = os.environ.get("ROMANA_API_URL", "http://127.0.0.1:8000")

# -------------------------------------------------------
# CREAR DIRECTORIOS SI NO EXISTEN
# -------------------------------------------------------
for directorio in [REPORTS_DIR, TEMPLATES_DIR]:
    os.makedirs(directorio, exist_ok=True)
