# ============================================================
# hardware/display_manager.py — Gestor del Display Activo
# ============================================================
# Este módulo actúa como PUNTO DE ENTRADA único para el hardware.
# El resto del sistema SOLO usa este manager, nunca los drivers
# directamente. Así podemos cambiar de marca sin tocar nada más.

from config import DISPLAY
from hardware.base_display import BaseDisplay
from hardware.display_simulator import DisplaySimulador
from hardware.display_toledo import DisplayToledo
from typing import Optional


# Display activo (singleton — solo uno a la vez)
_display_activo: Optional[BaseDisplay] = None


def obtener_display() -> Optional[BaseDisplay]:
    """Retorna el display actualmente activo."""
    return _display_activo


def inicializar_display(marca: str = None, puerto: str = None, baudrate: int = None) -> dict:
    """
    Inicializa el display según la configuración.
    Por defecto usa los valores de config.py.

    Args:
        marca:    "Toledo", "Simulador" (si None, usa config.py)
        puerto:   Puerto COM (si None, usa config.py)
        baudrate: Baudios (si None, usa config.py)

    Returns:
        dict con "exito", "mensaje" y "display"
    """
    global _display_activo

    marca    = marca    or DISPLAY["marca"]
    puerto   = puerto   or DISPLAY["puerto"]
    baudrate = baudrate or DISPLAY["baudrate"]

    # Desconectar el anterior si existe
    if _display_activo and _display_activo.esta_conectado():
        _display_activo.desconectar()

    # Crear el driver según la marca
    if marca.lower() == "simulador":
        display = DisplaySimulador()
    elif marca.lower() == "toledo":
        display = DisplayToledo(puerto=puerto, baudrate=baudrate)
    else:
        return {
            "exito": False,
            "mensaje": f"Marca '{marca}' no soportada. Marcas disponibles: Toledo, Simulador",
            "display": None
        }

    # Conectar
    if display.conectar():
        _display_activo = display
        return {"exito": True, "mensaje": f"Display {marca} conectado en {puerto}", "display": display}
    else:
        return {
            "exito": False,
            "mensaje": f"No se pudo conectar al display {marca} en {puerto}",
            "display": None
        }


def leer_peso_actual() -> Optional[float]:
    """
    Lee el peso del display activo.
    Retorna None si no hay display conectado.
    """
    if _display_activo and _display_activo.esta_conectado():
        return _display_activo.leer_peso()
    return None


def es_peso_estable() -> bool:
    """Verifica si el peso actual está estabilizado."""
    if _display_activo and _display_activo.esta_conectado():
        return _display_activo.peso_estable()
    return False


def desconectar_display():
    """Desconecta el display activo."""
    global _display_activo
    if _display_activo:
        _display_activo.desconectar()
        _display_activo = None
