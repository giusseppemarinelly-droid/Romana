# ============================================================
# gui/async_utils.py — Carga de datos en segundo plano para la GUI
# ============================================================
# Todas las pantallas hacían sus llamadas HTTP (api_client.listar_*)
# de forma síncrona, en el hilo principal de Tkinter, durante su
# propia construcción -- cada navegación bloqueaba la ventana entera
# mientras esperaba la respuesta del backend, sin ningún feedback.
# Bajo latencia normal (5-20ms) no se notaba, pero cualquier hipo de
# red (antivirus corporativo, Wi-Fi de planta, VPN) se sentía como que
# "se pegaba" al cambiar de pantalla.
#
# `cargar_en_hilo()` sigue el mismo patrón que ya usa client/ws_client.py
# para los eventos de WebSocket: el trabajo de red corre en un hilo
# aparte que NUNCA toca widgets de Tk (Tcl/Tk no lo garantiza seguro),
# y solo escribe en una queue.Queue (thread-safe por diseño). El hilo
# principal la vacía con su propio after() -- ahí, y solo ahí, es
# seguro tocar widgets.

import queue
import threading
from typing import Callable


def cargar_en_hilo(widget, fn: Callable, on_exito: Callable, on_error: Callable = None, intervalo_ms: int = 50):
    """
    Ejecuta fn() en un hilo de fondo; cuando termina, entrega el
    resultado a on_exito(resultado) (o la excepción a on_error(exc))
    en el hilo principal de Tkinter, vía after().

    fn:        SOLO I/O (llamadas a api_client) -- nunca debe tocar
               widgets de Tk.
    on_exito:  corre en el hilo principal, puede tocar widgets con
               seguridad. Si `widget` ya fue destruido cuando fn()
               termina, no se llama (evita el bug de los timers
               fantasma que seguían escribiendo en widgets muertos).
    on_error:  igual que on_exito pero para excepciones. Si se omite,
               los errores se descartan silenciosamente (igual que
               hacía el código síncrono original en varios lugares).
    """
    resultado_cola: "queue.Queue[tuple]" = queue.Queue()

    def worker():
        try:
            resultado_cola.put(("ok", fn()))
        except Exception as e:
            resultado_cola.put(("error", e))

    threading.Thread(target=worker, daemon=True).start()

    def _poll():
        try:
            tipo, valor = resultado_cola.get_nowait()
        except queue.Empty:
            if not widget.winfo_exists():
                return
            widget.after(intervalo_ms, _poll)
            return

        if not widget.winfo_exists():
            return  # la pantalla se destruyó (navegación) mientras esperábamos

        if tipo == "ok":
            on_exito(valor)
        elif on_error:
            on_error(valor)

    widget.after(intervalo_ms, _poll)
