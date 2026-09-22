# ============================================================
# gui/centro_costos/auto_aprobadas_view.py — Auto-aprobadas (solo lectura)
# ============================================================
# Antes vivía como un segundo panel apretado debajo de la cola de
# aprobaciones en centro_costos_view.py -- dejaba la Cola de
# Aprobaciones (donde realmente se trabaja: aprobar/rechazar) chica y
# con scroll para nada, y este panel de solo lectura casi siempre vacío
# ocupando media pantalla igual. Separado en su propia pantalla para que
# ambas tengan el alto completo.

import customtkinter as ctk
from tkinter import messagebox, ttk
from datetime import datetime
from config import UI
from client.api_client import api_client, ApiError
from client.ws_client import WsClient
from gui.async_utils import cargar_en_hilo
from gui.components.ui_kit import Card, titulo_h1, texto_ayuda, boton_secundario


def _fecha_hora(iso_str):
    if not iso_str:
        return "—"
    return datetime.fromisoformat(iso_str).strftime("%d/%m/%Y %H:%M")


class AutoAprobadasView(ctk.CTkFrame):
    """
    Pesadas que se aprobaron solas por tener la diferencia
    peso_guía/peso_neto dentro de tolerancia. Centro de Costos no
    decide nada acá (por eso no hay Aprobar/Rechazar) -- es solo para
    que la info le llegue igual, sin que el operador tenga que ir a
    buscarla al Kardex.
    """

    def __init__(self, parent, callback_navegar=None):
        super().__init__(parent, fg_color="transparent")
        self.callback_navegar = callback_navegar
        self._construir()
        self._cargar()

        # Mismo criterio que centro_costos_view.py: refresco en vivo por
        # WebSocket en vez de depender solo del botón "Actualizar".
        self._ws = WsClient(
            token=api_client.token,
            widget=self,
            on_evento=self._on_evento_ws,
            on_reconectar=self._cargar,
        )
        self._ws.iniciar()
        self.bind("<Destroy>", self._on_destroy)

    def _on_destroy(self, event):
        if event.widget is self:
            self._ws.detener()

    def _on_evento_ws(self, evento: dict):
        if evento.get("tipo") == "pesada_auto_aprobada":
            self._cargar()

    # ----------------------------------------------------------
    def _construir(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 12))
        header.grid_columnconfigure(0, weight=1)

        titulo_h1(header, "Auto-Aprobadas Recientes").grid(row=0, column=0, sticky="w")
        texto_ayuda(
            header,
            "Solo lectura -- pesadas aprobadas automáticamente por estar "
            "dentro de tolerancia contra el peso de guía."
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        card = Card(self)
        card.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 20))
        card.grid_rowconfigure(1, weight=1)
        card.grid_columnconfigure(0, weight=1)

        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(16, 8))
        top_row.grid_columnconfigure(0, weight=1)

        self._lbl_count = ctk.CTkLabel(
            top_row, text="0 pesada(s)",
            font=ctk.CTkFont(family=UI["fuente"], size=11),
            text_color=UI["color_muted"]
        )
        self._lbl_count.grid(row=0, column=0, sticky="w")

        boton_secundario(
            top_row, "↻  Actualizar", command=self._cargar, height=30, width=120,
        ).grid(row=0, column=1, sticky="e")

        style = ttk.Style()
        style.theme_use("default")
        style.configure("CCAuto.Treeview",
            background=UI["color_card"],
            foreground=UI["color_text"],
            fieldbackground=UI["color_input_bg"],
            rowheight=30,
            font=("Segoe UI", 11)
        )
        style.configure("CCAuto.Treeview.Heading",
            background=UI["color_bg"],
            foreground=UI["color_success"],
            font=("Segoe UI", 10, "bold")
        )

        cols = ("ticket", "placa", "fecha", "codigo_viaje", "peso_guia",
                "neto", "diferencia", "bultos")
        self._tree = ttk.Treeview(card, columns=cols, show="headings",
                                   style="CCAuto.Treeview", selectmode="none")

        configs = [
            ("ticket",       "TICKET",         90),
            ("placa",        "PLACA",          80),
            ("fecha",        "FECHA",         120),
            ("codigo_viaje", "COD. VIAJE",    110),
            ("peso_guia",    "PESO GUÍA",     100),
            ("neto",         "NETO KG",       100),
            ("diferencia",   "DIF. %",         80),
            ("bultos",       "BULTOS",         80),
        ]
        for col, titulo, ancho in configs:
            self._tree.heading(col, text=titulo)
            self._tree.column(col, width=ancho, minwidth=60)

        scroll = ttk.Scrollbar(card, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll.set)
        self._tree.grid(row=1, column=0, sticky="nsew", padx=(16, 0), pady=(0, 16))
        scroll.grid(row=1, column=1, sticky="ns", pady=(0, 16), padx=(0, 8))

    # ----------------------------------------------------------
    def _cargar(self):
        cargar_en_hilo(
            self, api_client.listar_auto_aprobadas,
            on_exito=self._poblar,
            on_error=lambda e: messagebox.showerror("Error de conexión", str(e)),
        )

    def _poblar(self, pesadas):
        for item in self._tree.get_children():
            self._tree.delete(item)

        for p in pesadas:
            neto = float(p["peso_neto"] or 0)
            peso_guia = float(p["peso_guia"] or 0)
            diferencia = abs(neto - peso_guia) / peso_guia * 100 if peso_guia else 0
            self._tree.insert("", "end", iid=str(p["id"]), values=(
                p["numero_ticket"],
                p["vehiculo"]["placa"] if p["vehiculo"] else "—",
                _fecha_hora(p["fecha_captura"]),
                p["codigo_viaje"] or "—",
                f"{peso_guia:,.0f}",
                f"{neto:,.0f}",
                f"{diferencia:,.2f}",
                p["bultos"] if p["bultos"] is not None else "—",
            ))

        self._lbl_count.configure(text=f"{len(pesadas)} pesada(s)")
