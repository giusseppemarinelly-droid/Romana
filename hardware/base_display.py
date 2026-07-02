# ============================================================
# hardware/base_display.py — Clase base abstracta para displays
# ============================================================
# ¿Por qué una clase abstracta?
#   Queremos que todos los displays (Toledo, Mettler, Avery, etc.)
#   tengan la MISMA interfaz. Así, el resto del sistema no necesita
#   saber qué marca es; siempre llama a los mismos métodos.
#
#   Patrón de diseño: STRATEGY
#   El comportamiento (lectura del peso) cambia según la marca,
#   pero la interfaz siempre es la misma.

from abc import ABC, abstractmethod
from typing import Optional


class BaseDisplay(ABC):
    """
    Clase abstracta que define la interfaz que TODOS los displays
    de pesaje deben implementar.

    Regla: Si defines un display nuevo, DEBES implementar todos
    los métodos marcados con @abstractmethod.
    """

    def __init__(self, puerto: str, baudrate: int = 9600, timeout: int = 2):
        """
        Args:
            puerto:   Puerto serial (ej: "COM1", "COM3")
            baudrate: Velocidad de comunicación (9600 estándar Toledo)
            timeout:  Segundos a esperar respuesta
        """
        self.puerto = puerto
        self.baudrate = baudrate
        self.timeout = timeout
        self.conectado = False

    @abstractmethod
    def conectar(self) -> bool:
        """
        Abre la conexión con el display.
        Returns: True si conectó, False si falló.
        """
        pass

    @abstractmethod
    def desconectar(self):
        """Cierra la conexión con el display."""
        pass

    @abstractmethod
    def leer_peso(self) -> Optional[float]:
        """
        Lee el peso actual del display.
        Returns: Peso en KG como float, o None si hay error.
        """
        pass

    @abstractmethod
    def peso_estable(self) -> bool:
        """
        Verifica si el peso está estabilizado (no está oscilando).
        Returns: True si estable, False si en movimiento.
        """
        pass

    def esta_conectado(self) -> bool:
        """Indica si la conexión está activa."""
        return self.conectado

    def __str__(self):
        estado = "conectado" if self.conectado else "desconectado"
        return f"{self.__class__.__name__} ({self.puerto}) - {estado}"
