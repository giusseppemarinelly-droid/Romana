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
# APARIENCIA DE LA INTERFAZ — Sistema de diseño propio
# -------------------------------------------------------
# Ver docs/design-system.md para la spec completa (paleta con
# justificación, tipografía, espaciado, componentes base) -- acá solo
# los valores. El navy de marca es el color real del logo de Sura
# (reports/templates/logo.png), muestreado a nivel de píxel, no a ojo.
# Mismas claves que la paleta anterior (para no tener que tocar cada
# pantalla que ya lee UI["color_accent"] etc.), valores nuevos.
UI = {
    "tema":               "light",

    # ── Marca (navy real de Sura) ──────────────────
    "color_brand":        "#1E2B50",   # Estructura: sidebar, headers, texto de máxima jerarquía
    "color_brand_hover":  "#28365C",
    "color_brand_tint":   "#EEF1F8",   # Filas activas/seleccionadas

    # ── Acción (ámbar industrial -- no otro azul más) ──
    "color_accent":       "#C1802A",
    "color_accent_hover": "#A2681E",
    "color_accent_tint":  "#FBF1E3",

    # Fondos
    "color_bg":           "#F4F1EC",   # Neutral cálido (no "slate" frío)
    "color_card":         "#FFFFFF",

    # Textos
    "color_text":         "#211F1D",
    "color_muted":        "#5C5750",

    # Bordes
    "color_border":       "#D8D3CB",

    # Campos de entrada (entries, comboboxes) — fondo levemente
    # distinto de las tarjetas para que se noten como "editables"
    "color_input_bg":      "#F4F1EC",

    # Estados
    "color_success":       "#1F7A4D",
    "color_success_hover": "#175E3B",
    "color_warning":       "#B5461F",
    "color_danger":        "#B42318",
    "color_danger_hover":  "#8F1B13",
    "color_info":          "#2A5FA5",

    # Estado de la báscula (semántica propia, no reutiliza los de
    # arriba -- ver docs/design-system.md sección "Estado de la báscula")
    "color_bascula_ok":        "#1F7A4D",
    "color_bascula_leyendo":   "#C1802A",
    "color_bascula_sin_senal": "#5C5750",
    "color_bascula_error":     "#B42318",

    # ── SIDEBAR ────────────────────────────────────
    "color_sidebar":        "#1E2B50",   # Navy de marca
    "color_sidebar_text":   "#E8E5DE",
    "color_sidebar_hover":  "#28365C",
    "color_sidebar_active": "#C1802A",   # Ítem activo -- color de acción, no un azul más
    "color_sidebar_section":"#9FB0D6",   # Navy claro legible sobre navy oscuro
    "color_sidebar_bottom": "#141D38",

    # Tipografía -- Segoe UI en todo (requisito del proyecto, ver CLAUDE.md)
    "fuente":             "Segoe UI",
    "fuente_size":        12,   # base/compat, queda por si algo viejo lo usa
    "fuente_display":     44,   # el peso de báscula -- el elemento más grande de la app
    "fuente_h1":          22,
    "fuente_h2":          15,
    "fuente_body":        13,
    "fuente_label":       11,
    "fuente_caption":     11,

    # Espaciado -- escala de 4px, nada fuera de esta lista
    "espaciado": {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24, "xxl": 32, "xxxl": 48},

    # Radios -- jerarquía, nunca "todo redondo"
    "radio_control": 6,   # inputs, botones, badges
    "radio_card":    10,  # tarjetas, paneles
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
