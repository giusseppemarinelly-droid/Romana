# ============================================================
# hardware/display_toledo.py — Driver para Displays Toledo
# ============================================================
# Toledo es una de las marcas más populares en básculas industriales.
# Sus displays se comunican por puerto serial (RS-232 o USB-Serial)
# usando un protocolo simple de texto ASCII.
#
# Protocolo Toledo Standard:
#   → PC envía:   "W\r\n"  (solicitar peso)
#   ← Display responde: "+  025340 KG\r\n"
#
# El formato de respuesta varía según el modelo exacto, pero
# este driver cubre la mayoría de los modelos Toledo Industrial.

import time
from typing import Optional

# Importamos pyserial para comunicación serial
# Si no está instalado: pip install pyserial
try:
    import serial
    SERIAL_DISPONIBLE = True
except ImportError:
    SERIAL_DISPONIBLE = False
    print("⚠️  pyserial no instalado. Instala con: pip install pyserial")

from hardware.base_display import BaseDisplay


class DisplayToledo(BaseDisplay):
    """
    Driver para displays/indicadores de peso marca Toledo.
    Compatible con modelos: 8142, 8141, 9510, IND131, IND331.

    Protocolo:
      Solicitud: 'W\\r\\n'
      Respuesta: '+  025340 KG ST\\r\\n'
        '+' = positivo
        '025340' = peso en KG (6 dígitos)
        'ST' = stable (peso estabilizado)
        'US' = unstable (en movimiento)
    """

    # Comandos del protocolo Toledo
    CMD_PESO = b"W\r\n"          # Solicitar lectura de peso
    CMD_ZERO = b"Z\r\n"          # Poner en cero
    CMD_TARA = b"T\r\n"          # Tarar

    def __init__(self, puerto: str = "COM1", baudrate: int = 9600, timeout: int = 2):
        super().__init__(puerto, baudrate, timeout)
        self._serial: Optional["serial.Serial"] = None
        self._ultimo_peso: Optional[float] = None
        self._ultimo_estable: bool = False

    def conectar(self) -> bool:
        """
        Abre el puerto serial y establece conexión con el display Toledo.
        """
        if not SERIAL_DISPONIBLE:
            print("❌ No se puede conectar: pyserial no está instalado")
            return False

        try:
            self._serial = serial.Serial(
                port=self.puerto,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,    # 8 bits de datos
                parity=serial.PARITY_NONE,    # Sin paridad
                stopbits=serial.STOPBITS_ONE, # 1 bit de stop
                timeout=self.timeout
            )

            if self._serial.is_open:
                self.conectado = True
                print(f"✅ Display Toledo conectado en {self.puerto} a {self.baudrate} bps")
                return True
            return False

        except serial.SerialException as e:
            print(f"❌ Error al conectar con display Toledo en {self.puerto}: {e}")
            self.conectado = False
            return False

    def desconectar(self):
        """Cierra el puerto serial."""
        if self._serial and self._serial.is_open:
            self._serial.close()
        self.conectado = False
        print(f"🔌 Display Toledo desconectado de {self.puerto}")

    def leer_peso(self) -> Optional[float]:
        """
        Solicita y lee el peso actual del display Toledo.

        Protocolo:
          1. Envía 'W\\r\\n' al display
          2. Lee la respuesta (ej: '+  025340 KG ST\\r\\n')
          3. Parsea el número de peso
          4. Retorna como float

        Returns:
            Peso en KG o None si hay error de comunicación.
        """
        if not self.conectado or not self._serial:
            return None

        try:
            # Limpiar buffer de entrada antes de solicitar
            self._serial.reset_input_buffer()

            # Enviar comando de solicitud de peso
            self._serial.write(self.CMD_PESO)

            # Esperar y leer la respuesta
            respuesta = self._serial.readline()

            if not respuesta:
                print("⚠️  Timeout: Display Toledo no respondió")
                return None

            # Decodificar y parsear la respuesta
            peso, estable = self._parsear_respuesta(respuesta.decode("ascii", errors="ignore"))

            if peso is not None:
                self._ultimo_peso = peso
                self._ultimo_estable = estable

            return peso

        except Exception as e:
            print(f"❌ Error al leer peso del display Toledo: {e}")
            return None

    def peso_estable(self) -> bool:
        """
        Retorna si el último peso leído estaba estabilizado.
        El display Toledo indica esto con 'ST' al final de la trama.
        """
        return self._ultimo_estable

    def _parsear_respuesta(self, respuesta: str):
        """
        Parsea la respuesta del display Toledo.

        Formato esperado: '+  025340 KG ST'
          [0]     = signo ('+' o '-')
          [1:9]   = peso con espacios
          [9:11]  = unidad ('KG' o 'LB')
          [12:14] = estado ('ST'=estable, 'US'=inestable)

        Returns:
            Tupla (peso_float, es_estable) o (None, False) si error.
        """
        respuesta = respuesta.strip()

        if not respuesta:
            return None, False

        try:
            # Intentar extraer el número de la respuesta
            # La respuesta puede variar entre modelos Toledo
            partes = respuesta.split()

            # Buscar el número de peso en las partes
            peso = None
            for parte in partes:
                # Limpiar signos y verificar si es número
                limpio = parte.replace("+", "").replace("-", "")
                if limpio.replace(".", "").isdigit() and len(limpio) > 0:
                    peso = float(limpio)
                    if parte.startswith("-"):
                        peso = -peso
                    break

            if peso is None:
                return None, False

            # Verificar estabilidad (buscar 'ST' en la respuesta)
            estable = "ST" in respuesta and "US" not in respuesta

            return abs(peso), estable  # Retornar valor absoluto

        except (ValueError, IndexError) as e:
            print(f"⚠️  Error parsing respuesta Toledo '{respuesta}': {e}")
            return None, False

    def poner_en_cero(self) -> bool:
        """Envía el comando de cero al display."""
        if not self.conectado:
            return False
        try:
            self._serial.write(self.CMD_ZERO)
            time.sleep(0.5)
            return True
        except Exception:
            return False

    def tarar(self) -> bool:
        """Envía el comando de tara al display."""
        if not self.conectado:
            return False
        try:
            self._serial.write(self.CMD_TARA)
            time.sleep(0.5)
            return True
        except Exception:
            return False
