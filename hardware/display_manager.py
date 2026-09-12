# ============================================================
# hardware/display_manager.py — Gestor del Display Activo
# ============================================================
# Este módulo actúa como PUNTO DE ENTRADA único para el hardware.
# El resto del sistema SOLO usa este manager, nunca los drivers
# directamente. Así podemos cambiar de marca sin tocar nada más.
#
# Lectura en un hilo de fondo dedicado (hallazgos C-04 y M-07):
#   leer_peso() del driver puede tardar hasta `timeout` segundos si la
#   báscula calla (cable flojo, display apagado, otro programa reteniendo
#   el puerto). Antes, la GUI llamaba leer_peso_actual() directo desde un
#   self.after() en el hilo principal de Tkinter -- cada tick bloqueaba
#   la ventana entera. Ahora un único hilo de fondo (iniciado por
#   inicializar_display(), nunca por la GUI) es quien de verdad toca el
#   driver; leer_peso_actual()/es_peso_estable() solo leen una variable
#   en memoria, protegida por lock, así que nunca bloquean. Ese mismo
#   hilo es también el único que toca el driver activo, lo que cierra de
#   paso M-07 (antes _display_activo era un global sin lock y el puerto
#   serie es un recurso exclusivo).
#
# Consistencia peso/estabilidad (hallazgo I-04): antes la GUI llamaba
# leer_peso_actual() y es_peso_estable() por separado sobre el mismo
# estado mutable del driver, pudiendo mezclar el peso de una lectura con
# la estabilidad de otra. Acá ambos salen de la MISMA lectura de fondo,
# tomada atómicamente bajo el mismo lock.

import threading
import time
from typing import Optional

from config import DISPLAY
from hardware.base_display import BaseDisplay
from hardware.display_simulator import DisplaySimulador
from hardware.display_toledo import DisplayToledo, detectar_puerto_toledo

# Confirmado en pruebas de campo 2026-09-12 (captura cruda con marca de
# tiempo, sin pasar por este módulo): el equipo cambia de trama cada
# 80-240ms y responde a una persona subiéndose/bajándose de la báscula
# en ~1s -- no tiene ningún filtro de varios segundos escondido. 0.25s
# le sigue el ritmo de cerca sin exigirle más de lo que ya transmite
# solo, y leer_peso_actual()/es_peso_estable() son lecturas en memoria
# (no tocan el puerto), así que no hay costo extra en sondear seguido.
_INTERVALO_LECTURA = 0.25  # segundos entre lecturas del hilo de fondo
_ANTIGUEDAD_MAX = 3.0     # lectura más vieja que esto se trata como "sin señal"

# Display activo (singleton — solo uno a la vez)
_display_activo: Optional[BaseDisplay] = None

_lock = threading.Lock()
_ultima_lectura = {"peso": None, "estable": False, "timestamp": 0.0}
_hilo_lector: Optional[threading.Thread] = None
_detener_hilo = threading.Event()


def obtener_display() -> Optional[BaseDisplay]:
    """Retorna el display actualmente activo."""
    return _display_activo


def _bucle_lector():
    while not _detener_hilo.is_set():
        display = _display_activo
        if display and display.esta_conectado():
            peso = display.leer_peso()
            estable = display.peso_estable() if peso is not None else False
            with _lock:
                _ultima_lectura["peso"] = peso
                _ultima_lectura["estable"] = estable
                _ultima_lectura["timestamp"] = time.time()
        _detener_hilo.wait(_INTERVALO_LECTURA)


def _iniciar_lectura_continua():
    global _hilo_lector
    if _hilo_lector is not None and _hilo_lector.is_alive():
        return
    with _lock:
        _ultima_lectura["peso"] = None
        _ultima_lectura["estable"] = False
        _ultima_lectura["timestamp"] = 0.0
    _detener_hilo.clear()
    _hilo_lector = threading.Thread(target=_bucle_lector, daemon=True, name="lector-bascula")
    _hilo_lector.start()


def _detener_lectura_continua():
    _detener_hilo.set()
    if _hilo_lector is not None and _hilo_lector.is_alive():
        _hilo_lector.join(timeout=_INTERVALO_LECTURA * 4)


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

    # Detener el hilo de lectura y desconectar el display anterior, si
    # había uno, antes de reemplazarlo -- nunca dos hilos leyendo drivers
    # distintos a la vez.
    _detener_lectura_continua()
    if _display_activo and _display_activo.esta_conectado():
        _display_activo.desconectar()
    _display_activo = None

    # Crear el driver según la marca
    if marca.lower() == "simulador":
        display = DisplaySimulador()
    elif marca.lower() == "toledo":
        # puerto="AUTO" (o vacío): escanear todos los COM disponibles en
        # vez de fijar uno -- pensado para la tarjeta multipuerto de la
        # estación Romana, donde Windows puede reasignar el número de
        # puerto (reinstalación, driver nuevo, otro slot). Confirmado en
        # pruebas de campo 2026-09-12 que esto también resuelve probar el
        # sistema en otra máquina (laptop con su propio adaptador
        # USB-serial en un puerto distinto) sin tocar config.py.
        if not puerto or puerto.strip().upper() == "AUTO":
            puerto_detectado = detectar_puerto_toledo(baudrate=baudrate)
            if not puerto_detectado:
                return {
                    "exito": False,
                    "mensaje": "No se detectó ninguna báscula Toledo respondiendo en ningún puerto COM",
                    "display": None
                }
            puerto = puerto_detectado
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
        _iniciar_lectura_continua()
        return {"exito": True, "mensaje": f"Display {marca} conectado en {puerto}", "display": display}
    else:
        return {
            "exito": False,
            "mensaje": f"No se pudo conectar al display {marca} en {puerto}",
            "display": None
        }


def leer_peso_actual() -> Optional[float]:
    """
    Último peso conocido, leído por el hilo de fondo -- nunca toca el
    puerto serie directo, así que nunca bloquea a quien la llama.
    Retorna None si no hay display conectado o si la última lectura ya
    es demasiado vieja (báscula dejó de responder).
    """
    with _lock:
        peso = _ultima_lectura["peso"]
        antiguedad = time.time() - _ultima_lectura["timestamp"]
    if peso is None or antiguedad > _ANTIGUEDAD_MAX:
        return None
    return peso


def es_peso_estable() -> bool:
    """Estabilidad de la MISMA lectura que devolvió leer_peso_actual()."""
    with _lock:
        peso = _ultima_lectura["peso"]
        estable = _ultima_lectura["estable"]
        antiguedad = time.time() - _ultima_lectura["timestamp"]
    if peso is None or antiguedad > _ANTIGUEDAD_MAX:
        return False
    return estable


def desconectar_display():
    """Desconecta el display activo y detiene el hilo de lectura de fondo."""
    global _display_activo
    _detener_lectura_continua()
    if _display_activo:
        _display_activo.desconectar()
        _display_activo = None
    with _lock:
        _ultima_lectura["peso"] = None
        _ultima_lectura["estable"] = False
        _ultima_lectura["timestamp"] = 0.0
