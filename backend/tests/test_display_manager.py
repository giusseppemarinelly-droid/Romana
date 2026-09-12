# ============================================================
# test_display_manager.py — C-04/M-07: lectura en hilo de fondo
# ============================================================
# Hallazgos de la auditoría (commit c97fdcc): leer_peso() puede tardar
# hasta `timeout` segundos si la báscula calla, y se llamaba directo
# desde un self.after() del hilo principal de Tkinter -- congelaba toda
# la ventana (C-04). Además _display_activo era un global sin lock pese
# a que el puerto serie es un recurso exclusivo (M-07).
#
# Se prueba con el DisplaySimulador real (no requiere hardware) en vez
# de un doble, porque el propio inicializar_display() es quien arranca
# el hilo -- probarlo con el simulador ejercita el camino completo.

import time

from hardware import display_manager


def teardown_function(_fn):
    # No dejar el hilo de lectura vivo entre tests.
    display_manager.desconectar_display()


def test_inicializar_display_arranca_hilo_de_fondo_y_actualiza_lectura():
    resultado = display_manager.inicializar_display(marca="Simulador")
    assert resultado["exito"] is True

    # Da tiempo a que el hilo de fondo haga al menos una lectura.
    time.sleep(display_manager._INTERVALO_LECTURA + 0.3)

    assert display_manager.leer_peso_actual() is not None
    assert isinstance(display_manager.es_peso_estable(), bool)


def test_leer_peso_actual_no_bloquea():
    """
    A diferencia de llamar al driver directo, leer_peso_actual() solo
    lee una variable en memoria -- debe resolver en microsegundos, nunca
    cerca del timeout del driver (2s).
    """
    display_manager.inicializar_display(marca="Simulador")
    time.sleep(display_manager._INTERVALO_LECTURA + 0.3)

    inicio = time.time()
    for _ in range(50):
        display_manager.leer_peso_actual()
        display_manager.es_peso_estable()
    duracion = time.time() - inicio

    assert duracion < 0.5, f"leer_peso_actual()/es_peso_estable() tardaron {duracion:.3f}s en 50 llamadas"


def test_desconectar_display_detiene_el_hilo():
    display_manager.inicializar_display(marca="Simulador")
    time.sleep(display_manager._INTERVALO_LECTURA + 0.3)
    assert display_manager._hilo_lector is not None
    assert display_manager._hilo_lector.is_alive()

    display_manager.desconectar_display()

    assert not display_manager._hilo_lector.is_alive()
    assert display_manager.obtener_display() is None
    assert display_manager.leer_peso_actual() is None


def test_leer_peso_actual_none_sin_display_inicializado():
    display_manager.desconectar_display()  # estado limpio, sin display
    assert display_manager.leer_peso_actual() is None
    assert display_manager.es_peso_estable() is False


def test_reinicializar_display_no_deja_dos_hilos_corriendo():
    display_manager.inicializar_display(marca="Simulador")
    time.sleep(display_manager._INTERVALO_LECTURA + 0.2)
    primer_hilo = display_manager._hilo_lector

    display_manager.inicializar_display(marca="Simulador")
    time.sleep(display_manager._INTERVALO_LECTURA + 0.2)
    segundo_hilo = display_manager._hilo_lector

    assert primer_hilo is not segundo_hilo
    assert not primer_hilo.is_alive(), "el hilo viejo debe quedar detenido, no corriendo en paralelo"
    assert segundo_hilo.is_alive()
