# ============================================================
# hardware/display_toledo.py — Driver para Displays Toledo
# ============================================================
# Toledo es una de las marcas más populares en básculas industriales.
# Sus displays se comunican por puerto serial (RS-232 o USB-Serial)
# usando un protocolo simple de texto ASCII.
#
# Protocolo real confirmado en planta (2026-07-23, display físico de
# la estación Romana, vía diagnóstico con PowerShell -- ver CLAUDE.md
# sección "Conexión física de la báscula"):
#   El display transmite SOLO, en continuo, cada cierto intervalo,
#   sin necesidad de pedir nada -- ignora el comando 'W\r\n' (la
#   respuesta con y sin haberlo enviado fue idéntica).
#   Trama: "ST,GS,+      0kg\r\n"
#     "ST"      = estado (ST=estable, US=inestable -- inferido por
#                 convención estándar, no confirmado en sitio porque
#                 la báscula estaba vacía durante la prueba)
#     "GS"      = modo (GS=peso bruto/gross, NT=neto -- no relevante
#                 para este sistema, el neto se calcula en software)
#     "+"       = signo
#     "      0" = peso, ancho fijo con relleno de espacios a la
#                 izquierda (ancho exacto del campo de dígitos sin
#                 confirmar más allá de 1 dígito, por la misma razón)
#     "kg"      = unidad, pegada al número sin espacio, minúscula
#
# Formato viejo que este driver asumía antes de la validación en
# planta ("+  025340 KG ST\r\n", con espacios como separador) --
# se mantiene el comando CMD_PESO por compatibilidad/inocuo, pero
# el parser ya no depende de que el display responda a él.

import re
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

    Protocolo (confirmado en planta 2026-07-23, ver comentario al
    inicio del archivo): el display transmite solo, en continuo.
      Trama: 'ST,GS,+      0kg\\r\\n'
        'ST' = estado (ST=estable, US=inestable)
        'GS' = modo (GS=bruto, NT=neto -- ignorado, no se usa)
        '+' = signo
        '      0' = peso, ancho fijo con relleno de espacios
        'kg' = unidad, pegada al número sin espacio
    """

    # Comandos del protocolo Toledo "clásico" -- el display real de
    # esta planta los ignora (transmite solo, en continuo), pero se
    # mantiene el envío por si algún otro modelo Toledo sí los usa.
    CMD_PESO = b"W\r\n"          # Solicitar lectura de peso
    CMD_ZERO = b"Z\r\n"          # Poner en cero
    CMD_TARA = b"T\r\n"          # Tarar

    _PATRON_RESPUESTA = re.compile(
        r"^(?P<estado>ST|US|OL|OV),(?P<modo>GS|NT),(?P<signo>[+-])\s*"
        r"(?P<valor>\d+(?:[.,]\d+)?)\s*(?P<unidad>kg|KG|lb|LB)$"
    )

    # Estados que no son una lectura válida de peso: la báscula está fuera de
    # rango. Se distinguen de "no entendí la trama" para que el operador vea
    # una sobrecarga como sobrecarga y no como "sin señal".
    _ESTADOS_DE_ERROR = {"OL": "sobrecarga", "OV": "sobrecarga"}

    # Cuántas líneas leer antes de rendirse en una sola llamada a leer_peso().
    # El display transmite en continuo, así que tras vaciar el buffer la
    # primera línea que llega casi siempre es la cola de una trama cortada a la
    # mitad: hay que poder descartarla y quedarse con la siguiente entera.
    # Cuatro alcanza de sobra y acota el tiempo total del peor caso.
    _MAX_LINEAS_POR_LECTURA = 4

    def __init__(self, puerto: str = "COM1", baudrate: int = 9600, timeout: int = 2):
        super().__init__(puerto, baudrate, timeout)
        self._serial: Optional["serial.Serial"] = None
        self._ultimo_peso: Optional[float] = None
        self._ultimo_estable: bool = False
        self._ultimo_error: Optional[str] = None

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
          1. Envía 'W\\r\\n' al display (el display lo ignora, ya
             transmite solo -- se manda igual por si acaso)
          2. Lee la próxima línea disponible (ej: 'ST,GS,+      0kg\\r\\n')
          3. Parsea el número de peso
          4. Retorna como float

        Returns:
            Peso en KG o None si hay error de comunicación.
        """
        if not self.conectado or not self._serial:
            return None

        self._ultimo_error = None

        try:
            # Vaciar el buffer para leer el peso de AHORA y no uno acumulado
            # hace varios segundos, que es justo lo que no sirve al capturar.
            self._serial.reset_input_buffer()

            # El display real de esta planta ignora el comando y transmite
            # solo; se manda igual por si otro modelo Toledo sí lo necesita.
            self._serial.write(self.CMD_PESO)

            # Leer hasta encontrar una trama entera. Vaciar el buffer deja el
            # cursor en medio de la transmisión en curso, así que la primera
            # línea suele ser un fragmento ('...,+  25340kg') que no parsea:
            # antes se devolvía None ahí mismo y la lectura se perdía. Ahora se
            # descarta y se sigue con la siguiente.
            for intento in range(self._MAX_LINEAS_POR_LECTURA):
                linea = self._serial.readline()

                if not linea:
                    # readline vacío = venció el timeout, no hay nada llegando.
                    # Se corta acá en vez de reintentar: cada intento más
                    # costaría otro timeout completo bloqueando al llamador.
                    self._ultimo_error = "sin respuesta"
                    self._ultimo_estable = False
                    print("⚠️  Timeout: Display Toledo no respondió")
                    return None

                peso, estable, error = self._parsear_respuesta(
                    linea.decode("ascii", errors="ignore")
                )

                if error:
                    # Fuera de rango: es una respuesta válida del display, no
                    # una trama rota. No tiene sentido seguir leyendo.
                    self._ultimo_error = error
                    self._ultimo_estable = False
                    print(f"⚠️  Display Toledo reporta {error}")
                    return None

                if peso is not None:
                    self._ultimo_peso = peso
                    self._ultimo_estable = estable
                    return peso

                # Trama ilegible (fragmento o ruido): probar con la siguiente.

            self._ultimo_error = "tramas ilegibles"
            self._ultimo_estable = False
            print(f"⚠️  {self._MAX_LINEAS_POR_LECTURA} tramas seguidas ilegibles del display Toledo")
            return None

        except Exception as e:
            self._ultimo_error = str(e)
            self._ultimo_estable = False
            print(f"❌ Error al leer peso del display Toledo: {e}")
            return None

    def ultimo_error(self) -> Optional[str]:
        """Por qué falló la última lectura ("sobrecarga", "sin respuesta",
        "tramas ilegibles"), o None si salió bien. Permite que la GUI
        distinguya una báscula sobrecargada de una desconectada."""
        return self._ultimo_error

    def peso_estable(self) -> bool:
        """
        Retorna si el último peso leído estaba estabilizado.
        El display Toledo indica esto con 'ST' al inicio de la trama.
        """
        return self._ultimo_estable

    def _parsear_respuesta(self, respuesta: str):
        """
        Parsea una trama del display Toledo.

        Formato real (ver docstring de la clase): 'ST,GS,+      0kg'

        Returns:
            Tupla (peso, es_estable, error):
              (25340.0, True,  None)          trama válida y estable
              (None,    False, "sobrecarga")  el display avisa fuera de rango
              (None,    False, None)          trama ilegible -- probar la siguiente
        """
        respuesta = respuesta.strip()

        if not respuesta:
            return None, False, None

        match = self._PATRON_RESPUESTA.match(respuesta)
        if not match:
            # Sin print: con un display que transmite en continuo, la primera
            # línea tras vaciar el buffer es normalmente un fragmento, y
            # avisarlo en cada lectura llenaría la consola de ruido esperado.
            return None, False, None

        error = self._ESTADOS_DE_ERROR.get(match.group("estado"))
        if error:
            return None, False, error

        # Coma decimal por si el display está configurado en formato europeo.
        peso = float(match.group("valor").replace(",", "."))
        if match.group("signo") == "-":
            peso = -peso

        # El signo se conserva a propósito. Antes se devolvía abs(), así que un
        # peso negativo -- celda de carga descalibrada, basura sobre la
        # plataforma, tara mal puesta -- se convertía en un peso positivo
        # plausible y entraba al sistema como bueno. Quien captura ya exige
        # peso > 0, así que devolverlo con signo hace que se rechace solo.
        estable = match.group("estado") == "ST"
        return peso, estable, None

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
