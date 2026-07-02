# ============================================================
# hardware/display_simulator.py — Simulador de Display de Pesaje
# ============================================================
# Este módulo SIMULA un display real para que puedas desarrollar
# y probar el sistema sin tener el hardware físico conectado.
#
# ¿Cómo funciona?
#   Genera pesos aleatorios realistas dentro de rangos configurables.
#   Simula el tiempo de estabilización (como haría un display real).
#   Perfectamente reemplazable por el driver real sin cambiar nada más.

import random
import time
from typing import Optional
from hardware.base_display import BaseDisplay


class DisplaySimulador(BaseDisplay):
    """
    Simulador de display de pesaje para desarrollo y pruebas.
    NO requiere hardware. Genera pesos aleatorios realistas.

    Uso:
        display = DisplaySimulador()
        display.conectar()
        peso = display.leer_peso()  # Devuelve un número como 25340.0
        display.desconectar()
    """

    def __init__(
        self,
        peso_min: float = 15000,   # KG mínimo simulado (15 toneladas)
        peso_max: float = 55000,   # KG máximo simulado (55 toneladas)
        variacion: float = 50,     # Variación de ±50 KG para simular oscilación
    ):
        # Llamar al constructor de la clase padre
        super().__init__(puerto="SIMULADOR", baudrate=9600, timeout=1)

        self.peso_min = peso_min
        self.peso_max = peso_max
        self.variacion = variacion

        # Peso "base" fijo para la sesión de simulación
        # (simula que hay un camión estacionado en la báscula)
        self._peso_base = random.uniform(peso_min, peso_max)
        self._estabilizando = False
        self._tiempo_inicio = None

    def conectar(self) -> bool:
        """Simula la conexión al display (siempre exitosa)."""
        print(f"🖥️  [SIMULADOR] Conectando al display simulado...")
        time.sleep(0.3)  # Simular delay de conexión
        self.conectado = True
        self._peso_base = random.uniform(self.peso_min, self.peso_max)
        # Redondear al múltiplo de 20 más cercano (como hacen las básculas reales)
        self._peso_base = round(self._peso_base / 20) * 20
        print(f"🖥️  [SIMULADOR] Conectado. Peso base: {self._peso_base:,.0f} KG")
        return True

    def desconectar(self):
        """Simula la desconexión."""
        self.conectado = False
        print("🖥️  [SIMULADOR] Display desconectado")

    def leer_peso(self) -> Optional[float]:
        """
        Genera un peso simulado con pequeña variación aleatoria.
        Simula la lectura real de la báscula.

        Returns:
            Peso en KG con variación de ±50 KG, o None si no está conectado.
        """
        if not self.conectado:
            return None

        # Agregar ruido aleatorio para simular oscilación real
        ruido = random.uniform(-self.variacion, self.variacion)
        peso = self._peso_base + ruido

        # Redondear al múltiplo de 20 (división de la báscula)
        peso = round(peso / 20) * 20

        return max(0.0, peso)  # No puede ser negativo

    def peso_estable(self) -> bool:
        """
        Simula si el peso está estabilizado.
        En un display real, esto se indica con un indicador de estabilidad.
        """
        if not self.conectado:
            return False

        # 85% de probabilidad de estar estable (simula realidad)
        return random.random() > 0.15

    def simular_camion_nuevo(self, peso: float = None):
        """
        Simula que llegó un camión diferente a la báscula.
        Útil para probar múltiples pesajes seguidos.

        Args:
            peso: Si se especifica, usa ese peso exacto.
                  Si no, genera uno aleatorio.
        """
        if peso is not None:
            self._peso_base = round(peso / 20) * 20
        else:
            self._peso_base = round(
                random.uniform(self.peso_min, self.peso_max) / 20
            ) * 20
        print(f"🚛 [SIMULADOR] Nuevo camión. Peso: {self._peso_base:,.0f} KG")

    def simular_camion_vacio(self):
        """Simula que salió la carga y quedó solo el camión (tara)."""
        # Un camión vacío pesa aproximadamente 30-40% de su peso con carga
        self._peso_base = round(self._peso_base * random.uniform(0.25, 0.35) / 20) * 20
        print(f"🚛 [SIMULADOR] Camión vacío. Tara: {self._peso_base:,.0f} KG")
