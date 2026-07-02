# ============================================================
# client/ws_client.py — Cliente WebSocket (reemplaza el botón manual
# "↻ Actualizar" por refresco automático en tiempo real)
# ============================================================
import json
import queue
import threading
import time
from typing import Callable, Optional

from websockets.sync.client import connect as ws_connect

from config import API_BASE_URL


def _url_websocket(token: str) -> str:
    url = API_BASE_URL.rstrip("/")
    if url.startswith("https://"):
        url = "wss://" + url[len("https://"):]
    elif url.startswith("http://"):
        url = "ws://" + url[len("http://"):]
    return f"{url}/ws/pesadas?token={token}"


class WsClient:
    """
    Corre la conexión WebSocket en un hilo aparte (daemon). El hilo del
    socket NUNCA toca Tkinter directamente — Tcl/Tk no garantiza que
    llamar a `widget.after()` desde un hilo distinto al principal sea
    seguro (es una causa conocida de cuelgues/errores intermitentes y
    difíciles de reproducir, particularmente en Windows). En cambio, el
    hilo del socket solo escribe en una `queue.Queue` (esa sí es
    thread-safe por diseño), y es el propio hilo principal el que se
    reprograma a sí mismo con `after()` para vaciarla periódicamente —
    ningún código de Tk se ejecuta jamás fuera del hilo principal.

    Reconexión con backoff exponencial (1s, 2s, 4s... hasta 30s tope):
    el WS es solo un canal de notificación best-effort — si se cae, al
    reconectar la vista debe resincronizar su estado con un GET normal
    (ver `on_reconectar` en centro_costos_view.py), nunca depender del
    WS como única fuente de verdad.
    """

    _POLL_MS = 150

    def __init__(self, token: str, widget, on_evento: Callable[[dict], None], on_reconectar: Optional[Callable[[], None]] = None):
        self._token = token
        self._widget = widget
        self._on_evento = on_evento
        self._on_reconectar = on_reconectar
        self._detener = threading.Event()
        self._cola: "queue.Queue[tuple]" = queue.Queue()
        self._hilo: Optional[threading.Thread] = None

    def iniciar(self):
        """Debe llamarse desde el hilo principal (Tkinter) — arranca el
        hilo del socket y el polling de la cola, ambos desde acá."""
        self._hilo = threading.Thread(target=self._loop, daemon=True)
        self._hilo.start()
        self._widget.after(self._POLL_MS, self._vaciar_cola)

    def detener(self):
        self._detener.set()

    # ------------------------------------------------------------
    # Hilo del socket — solo produce hacia la cola, nunca toca Tk.
    # ------------------------------------------------------------
    def _loop(self):
        backoff = 1
        primera_conexion = True
        while not self._detener.is_set():
            try:
                with ws_connect(_url_websocket(self._token), open_timeout=5) as ws:
                    backoff = 1
                    if not primera_conexion and self._on_reconectar:
                        self._cola.put(("reconectar", None))
                    primera_conexion = False

                    while not self._detener.is_set():
                        try:
                            mensaje = ws.recv(timeout=1)
                        except TimeoutError:
                            continue
                        try:
                            evento = json.loads(mensaje)
                        except (TypeError, ValueError):
                            continue
                        self._cola.put(("evento", evento))
            except Exception:
                if self._detener.is_set():
                    return
                time.sleep(backoff)
                backoff = min(backoff * 2, 30)

    # ------------------------------------------------------------
    # Hilo principal — se reprograma a sí mismo, único lugar que toca Tk.
    # ------------------------------------------------------------
    def _vaciar_cola(self):
        while True:
            try:
                tipo, payload = self._cola.get_nowait()
            except queue.Empty:
                break
            if tipo == "evento":
                self._on_evento(payload)
            elif tipo == "reconectar" and self._on_reconectar:
                self._on_reconectar()

        if self._detener.is_set():
            return
        try:
            self._widget.after(self._POLL_MS, self._vaciar_cola)
        except Exception:
            # El widget ya fue destruido (se navegó a otra pantalla).
            self._detener.set()
