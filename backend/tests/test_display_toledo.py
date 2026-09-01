# ============================================================
# backend/tests/test_display_toledo.py
# ============================================================
# El display de la planta transmite en continuo, así que vaciar el buffer deja
# el cursor en medio de una trama y la primera línea que llega suele ser un
# fragmento. Estos tests fijan ese comportamiento sin necesidad de hardware:
# un puerto falso entrega las líneas que se le indiquen.
import pytest

from hardware.display_toledo import DisplayToledo


class PuertoFalso:
    """Puerto serie de mentira: devuelve las líneas dadas, una por readline()."""

    def __init__(self, lineas):
        self.lineas = list(lineas)
        self.leidas = 0

    def reset_input_buffer(self):
        pass

    def write(self, datos):
        pass

    def readline(self):
        if not self.lineas:
            return b""  # readline vacío = venció el timeout
        self.leidas += 1
        return self.lineas.pop(0)


def _display_con(lineas):
    display = DisplayToledo()
    display.conectado = True
    display._serial = PuertoFalso(lineas)
    return display


def test_descarta_la_trama_parcial_y_usa_la_siguiente_entera():
    """
    Regresión del caso real: `reset_input_buffer()` seguido de `readline()`
    devolvía la cola de la trama que estaba transmitiéndose. El parser fallaba
    y leer_peso() devolvía None, así que en pantalla se veía "Sin señal" y una
    captura legítima se abortaba con "No hay un peso válido en la báscula".
    """
    display = _display_con([b",+  25340kg\r\n", b"ST,GS,+  25340kg\r\n"])
    assert display.leer_peso() == 25340.0
    assert display.peso_estable() is True
    assert display.ultimo_error() is None


def test_lee_una_trama_entera_sin_gastar_lecturas_de_mas():
    """Un display que sí responde al comando (otro modelo Toledo) tiene que
    resolverse en una sola lectura, no pagar el descarte de la primera."""
    display = _display_con([b"ST,GS,+  25340kg\r\n"])
    assert display.leer_peso() == 25340.0
    assert display._serial.leidas == 1


def test_marca_inestable_cuando_el_camion_se_esta_moviendo():
    display = _display_con([b"US,GS,+  25340kg\r\n"])
    assert display.leer_peso() == 25340.0
    assert display.peso_estable() is False


def test_la_sobrecarga_se_distingue_de_una_trama_ilegible():
    """
    'OL' no matcheaba el patrón, así que exceder la capacidad de la báscula se
    veía igual que un cable flojo. Son dos problemas muy distintos para quien
    está parado frente al camión.
    """
    display = _display_con([b"OL,GS,+  99999kg\r\n"])
    assert display.leer_peso() is None
    assert display.ultimo_error() == "sobrecarga"


def test_el_peso_negativo_conserva_el_signo():
    """
    Antes se devolvía abs(), así que una celda de carga descalibrada o basura
    sobre la plataforma daban un peso positivo plausible que entraba al sistema
    como bueno. Con el signo intacto, el chequeo de peso > 0 lo rechaza solo.
    """
    display = _display_con([b"ST,GS,-    100kg\r\n"])
    assert display.leer_peso() == -100.0


def test_acepta_coma_decimal():
    display = _display_con([b"ST,GS,+ 25340,5kg\r\n"])
    assert display.leer_peso() == 25340.5


def test_una_bascula_muda_no_reintenta():
    """
    Con el puerto en silencio, cada readline cuesta un timeout completo (2 s
    por defecto). Reintentar multiplicaría el bloqueo del llamador, que hoy es
    el hilo principal de Tkinter.
    """
    display = _display_con([])
    assert display.leer_peso() is None
    assert display.ultimo_error() == "sin respuesta"
    assert display._serial.leidas == 0


def test_se_rinde_ante_ruido_continuo_en_vez_de_leer_para_siempre():
    display = _display_con([b"xxx\r\n"] * 20)
    assert display.leer_peso() is None
    assert display.ultimo_error() == "tramas ilegibles"
    assert display._serial.leidas == DisplayToledo._MAX_LINEAS_POR_LECTURA


@pytest.mark.parametrize("trama,esperado", [
    (b"ST,GS,+      0kg\r\n", 0.0),        # la única confirmada en planta
    (b"ST,NT,+  25340kg\r\n", 25340.0),    # display puesto en modo neto
    (b"ST,GS,+  25340 kg\r\n", 25340.0),   # espacio antes de la unidad
    (b"ST,GS,+  25340kg\r", 25340.0),      # sin LF final
])
def test_variantes_de_trama_que_deben_parsear(trama, esperado):
    assert _display_con([trama]).leer_peso() == esperado
