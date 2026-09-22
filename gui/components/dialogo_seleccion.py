# ============================================================
# gui/components/dialogo_seleccion.py — Elegir de una lista (con filtro)
# ============================================================
# Se abre al apretar "Buscar" con el campo vacío -- separa las dos
# formas de encontrar algo: "sé lo que quiero, lo escribo y confirmo
# con Buscar" (el campo de texto de al lado, sin autocompletar
# mientras se escribe) de "no sé, quiero ver todo lo que hay" (este
# diálogo). Antes el campo de Vehículo mezclaba las dos en un solo
# combo con filtro en vivo -- se sentía ruidoso, pedido explícito del
# usuario (2026-09-17) separarlas.

import customtkinter as ctk
from config import UI
from gui.components.dialogo_alta_rapida import _ICONO_VENTANA
from gui.components.ui_kit import titulo_h2, boton_secundario, ocultar_scrollbar


class DialogoSeleccion(ctk.CTkToplevel):
    """
    Uso:
        DialogoSeleccion(
            self, titulo="Seleccionar vehículo",
            items=[("ABC-123 — Camión Ejemplo", vehiculo_dict), ...],
            on_elegido=lambda valor: ...,
        )
    `items` es una lista de (texto_a_mostrar, valor_a_devolver) -- el
    valor puede ser cualquier cosa (un dict del registro, un id, un
    string), lo que le sirva al que abre el diálogo.
    """

    _ALTO_FILA = 36
    _MAX_FILAS_VISIBLES = 9

    def __init__(self, parent, titulo, items, on_elegido):
        super().__init__(parent)
        self.withdraw()
        self.title(titulo)
        try:
            self.iconbitmap(_ICONO_VENTANA)
        except Exception:
            pass

        self._items = items
        self._on_elegido = on_elegido
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        self.configure(fg_color=UI["color_bg"])
        self.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(
            self, fg_color=UI["color_card"], corner_radius=UI["radio_card"],
            border_width=1, border_color=UI["color_border"],
        )
        card.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)

        stripe = ctk.CTkFrame(card, fg_color=UI["color_accent"], height=4, corner_radius=2)
        stripe.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 0))

        titulo_h2(card, titulo).grid(row=1, column=0, padx=24, pady=(14, 10), sticky="w")

        self._entry_filtro = ctk.CTkEntry(
            card, height=38, width=360,
            placeholder_text="Escriba para filtrar...",
            font=ctk.CTkFont(family=UI["fuente"], size=13),
            fg_color=UI["color_input_bg"], border_color=UI["color_border"],
            border_width=2, corner_radius=UI["radio_control"],
        )
        self._entry_filtro.grid(row=2, column=0, padx=24, pady=(0, 10), sticky="ew")
        self._entry_filtro.bind("<KeyRelease>", lambda e: self._refiltrar())

        alto_lista = min(len(items), self._MAX_FILAS_VISIBLES) * self._ALTO_FILA + 8
        alto_lista = max(alto_lista, self._ALTO_FILA + 8)
        self._lista = ctk.CTkScrollableFrame(
            card, fg_color=UI["color_bg"], corner_radius=UI["radio_control"],
            width=360, height=alto_lista,
        )
        self._lista.grid(row=3, column=0, padx=24, pady=(0, 12), sticky="ew")
        self._lista.grid_columnconfigure(0, weight=1)
        ocultar_scrollbar(self._lista)

        boton_secundario(card, "Cancelar", command=self.destroy).grid(
            row=4, column=0, padx=24, pady=(0, 24), sticky="ew")

        self._poblar(items)
        self._centrar_sobre_padre(parent)
        self.deiconify()
        self._entry_filtro.focus_set()

    def _centrar_sobre_padre(self, parent):
        # Ver comentario en dialogo_alta_rapida.DialogoAltaRapida
        # ._centrar_sobre_padre -- mismo criterio (wm_geometry, no
        # geometry, para no reescalar dos veces).
        self.update_idletasks()
        ancho = self.winfo_reqwidth()
        alto = self.winfo_reqheight()
        raiz = parent.winfo_toplevel()
        px = raiz.winfo_rootx() + (raiz.winfo_width() - ancho) // 2
        py = raiz.winfo_rooty() + (raiz.winfo_height() - alto) // 2
        self.wm_geometry(f"{ancho}x{alto}+{max(px, 0)}+{max(py, 0)}")

    def _refiltrar(self):
        texto = self._entry_filtro.get().strip().lower()
        if not texto:
            self._poblar(self._items)
            return
        filtrados = [it for it in self._items if texto in it[0].lower()]
        self._poblar(filtrados)

    def _poblar(self, items):
        for w in self._lista.winfo_children():
            w.destroy()

        if not items:
            ctk.CTkLabel(
                self._lista, text="Sin resultados",
                font=ctk.CTkFont(family=UI["fuente"], size=12),
                text_color=UI["color_muted"],
            ).grid(row=0, column=0, pady=12)
            return

        for i, (texto, valor) in enumerate(items):
            ctk.CTkButton(
                self._lista, text=texto, anchor="w",
                height=self._ALTO_FILA - 4,
                fg_color="transparent", hover_color=UI["color_card"],
                text_color=UI["color_text"],
                font=ctk.CTkFont(family=UI["fuente"], size=12),
                command=lambda v=valor: self._elegir(v),
            ).grid(row=i, column=0, sticky="ew", pady=1, padx=4)

    def _elegir(self, valor):
        self.destroy()
        self._on_elegido(valor)
