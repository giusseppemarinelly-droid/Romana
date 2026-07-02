# ============================================================
# client/ws_client.py — Cliente WebSocket (reemplaza el botón manual
# "↻ Actualizar" por refresco automático en tiempo real)
# ============================================================
import json
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
    Corre la conexión WebSocket en un hilo aparte (daemon) y despacha
    cada evento recibido al hilo principal de Tkinter vía
    `widget.after(0, ...)`. Tkinter NO es thread-safe: tocar widgets
    directamente desde el hilo del socket produciría errores
    intermitentes y difíciles de reproducir.

    Reconexión con backoff exponencial (1s, 2s, 4s... hasta 30s tope):
    el WS es solo un canal de notificación best-effort — si se cae, al
    reconectar la vista debe resincronizar su estado con un GET normal
    (ver `on_reconectar` en centro_costos_view.py), nunca depender del
    WS como única fuente de verdad.
    """

    def __init__(self, token: str, widget, on_evento: Callable[[dict], None], on_reconectar: Optional[Callable[[], None]] = None):
        self._token = token
        self._widget = widget
        self._on_evento = on_evento
        self._on_reconectar = on_reconectar
        self._detener = threading.Event()
        self._hilo: Optional[threading.Thread] = None

    def iniciar(self):
        self._hilo = threading.Thread(target=self._loop, daemon=True)
        self._hilo.start()

    def detener(self):
        self._detener.set()

    def _loop(self):
        backoff = 1
        primera_conexion = True
        while not self._detener.is_set():
            try:
                with ws_connect(_url_websocket(self._token), open_timeout=5) as ws:
                    backoff = 1
                    if not primera_conexion and self._on_reconectar:
                        self._en_hilo_tkinter(self._on_reconectar)
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
                        self._en_hilo_tkinter(lambda ev=evento: self._on_evento(ev))
            except Exception:
                if self._detener.is_set():
                    return
                time.sleep(backoff)
                backoff = min(backoff * 2, 30)

    def _en_hilo_tkinter(self, callback):
        try:
            self._widget.after(0, callback)
        except Exception:
            # El widget ya fue destruido (se navegó a otra pantalla).
            self._detener.set()
