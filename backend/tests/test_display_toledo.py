# ============================================================
# test_display_toledo.py — Driver de báscula Toledo (parser + lectura)
# ============================================================
# Cubre el hallazgo C-01 de la auditoría (commit c97fdcc): el driver
# descartaba erróneamente la primera trama tras reset_input_buffer(),
# reproducido en pruebas de campo el 2026-09-12 contra hardware real
# (COM3, laptop de pruebas) -- ver hardware/display_toledo.py:leer_peso().
#
# No requiere puerto serie real: _parsear_respuesta() es lógica pura,
# y leer_peso() se prueba con un doble de serial.Serial en memoria.

from hardware.display_toledo import DisplayToledo


def _driver():
    return DisplayToledo(puerto="COMX", baudrate=9600, timeout=2)


# ---------- _parsear_respuesta() ----------

def test_parsear_respuesta_peso_cero():
    peso, estable = _driver()._parsear_respuesta("ST,GS,+      0kg\r\n")
    assert peso == 0.0
    assert estable is True


def test_parsear_respuesta_peso_dos_digitos():
    peso, estable = _driver()._parsear_respuesta("ST,GS,+     10kg\r\n")
    assert peso == 10.0
    assert estable is True


def test_parsear_respuesta_inestable():
    peso, estable = _driver()._parsear_respuesta("US,GS,+     10kg\r\n")
    assert peso == 10.0
    assert estable is False


def test_parsear_respuesta_trama_cortada_no_matchea():
    # Trama real vista en campo: reset_input_buffer() cayó a mitad de
    # transmisión y perdió los primeros bytes ('ST,G' del inicio).
    peso, estable = _driver()._parsear_respuesta("S,+      0kg\r\n")
    assert peso is None
    assert estable is False


def test_parsear_respuesta_peso_negativo_propaga_signo():
    # Confirmado en pruebas de campo 2026-09-12: plataforma vacía marcando
    # 'ST,GS,-     70kg' con la báscula en medio de un ajuste mecánico.
    # Antes abs() convertía esto en un +70 plausible (parte del hallazgo
    # C-03) -- ahora debe devolver el negativo tal cual.
    peso, estable = _driver()._parsear_respuesta("ST,GS,-     70kg\r\n")
    assert peso == -70.0
    assert estable is True


def test_parsear_respuesta_vacia():
    peso, estable = _driver()._parsear_respuesta("")
    assert peso is None
    assert estable is False


# ---------- leer_peso(): descarta la primera línea tras el reset ----------

class _FakeSerial:
    """Doble mínimo de serial.Serial -- sólo lo que usa leer_peso()."""

    def __init__(self, lineas):
        self._lineas = list(lineas)
        self.reset_calls = 0
        self.written = []

    def reset_input_buffer(self):
        self.reset_calls += 1

    def write(self, data):
        self.written.append(data)

    def readline(self):
        return self._lineas.pop(0) if self._lineas else b""


def test_leer_peso_descarta_primera_linea_tras_reset():
    """
    La primera línea después de reset_input_buffer() puede venir cortada
    (el display transmite en continuo, sin pausas) -- leer_peso() debe
    descartarla y devolver la SIGUIENTE línea completa, no la primera.
    """
    d = _driver()
    d.conectado = True
    d._serial = _FakeSerial([
        b"S,+      0kg\r\n",       # cortada -- se descarta sin intentar parsear
        b"ST,GS,+     10kg\r\n",   # completa -- esta es la que debe devolver
    ])

    peso = d.leer_peso()

    assert peso == 10.0
    assert d.peso_estable() is True


def test_leer_peso_sin_datos_devuelve_none():
    d = _driver()
    d.conectado = True
    d._serial = _FakeSerial([])  # readline() devuelve b"" -- timeout

    assert d.leer_peso() is None


def test_leer_peso_no_conectado_devuelve_none():
    d = _driver()
    assert d.conectado is False
    assert d.leer_peso() is None


# ---------- conectar(): I-02, "conectado" exige señal real ----------

class _FakeSerialConectar(_FakeSerial):
    """Doble de serial.Serial también para conectar() -- agrega is_open/close."""

    def __init__(self, lineas, is_open=True):
        super().__init__(lineas)
        self.is_open = is_open
        self.cerrado = False

    def close(self):
        self.cerrado = True


def test_conectar_confirma_con_trama_valida(monkeypatch):
    import hardware.display_toledo as mod

    fake = _FakeSerialConectar([b"ST,GS,+      0kg\r\n"])
    monkeypatch.setattr(mod.serial, "Serial", lambda **kwargs: fake)

    d = mod.DisplayToledo(puerto="COMX")
    assert d.conectar() is True
    assert d.conectado is True


def test_conectar_rechaza_si_no_llega_ninguna_trama_valida(monkeypatch):
    """
    Hallazgo I-02: antes "conectado" significaba solo que el puerto COM
    abrió -- pasaba igual con el cable desconectado del lado del
    display. Ahora exige al menos una trama parseable dentro de los
    primeros intentos.
    """
    import hardware.display_toledo as mod

    # El puerto "abre" pero nunca llega nada -- cable desconectado del
    # otro lado, o display apagado.
    fake = _FakeSerialConectar([])
    monkeypatch.setattr(mod.serial, "Serial", lambda **kwargs: fake)

    d = mod.DisplayToledo(puerto="COMX")
    assert d.conectar() is False
    assert d.conectado is False
    assert fake.cerrado is True  # no deja el puerto abierto a medias
