# ============================================================
# gui/components/combo_buscable.py — Combo propio: filtra al escribir
# ============================================================
# Reemplaza CTkComboBox en los campos "elegí de la lista o escriba a
# mano" (Vehículo, Producto en Entrada de Camión, y cualquier pantalla
# parecida). Dos problemas de CTkComboBox que este widget resuelve:
#
#   1. El desplegable de opciones de CTkComboBox es el NATIVO de
#      Windows -- gris, sin el estilo azul/blanco del resto de la app,
#      y no filtra mientras se escribe (hay que scrollear a ojo una
#      lista larga, ej. el catálogo completo de vehículos).
#   2. CTkComboBox es un Entry normal por dentro: si ya tiene un valor
#      puesto (el placeholder "-- Seleccione --", o una selección
#      anterior) y el usuario empieza a escribir, el cursor por
#      defecto queda al final del texto existente -- tipear agrega
#      caracteres en vez de reemplazar, dejando cosas como
#      "-- Seleccione --asdf" en pantalla.
#
# API pensada como reemplazo directo de CTkComboBox en los usos que ya
# existían: .get(), .set(valor), .configure(values=[...]), y
# command=callback (se llama con el texto actual al confirmar una
# selección -- clic en una fila del desplegable, o Enter -- igual que
# CTkComboBox).
#
# A propósito NO tiene navegación con flechas del teclado ni
# auto-scroll a la fila resaltada -- se evaluó agregarlo, pero suma
# bastante código frágil (acceder al scroll interno de
# CTkScrollableFrame) para un beneficio chico frente a filtrar
# escribiendo + click, que ya cubre el caso de uso real de estos
# campos. Si hace falta más adelante, se puede agregar sin tocar la
# API pública.

import customtkinter as ctk
from config import UI
from gui.components.ui_kit import ocultar_scrollbar


class ComboBuscable(ctk.CTkFrame):
    _ALTO_FILA = 34
    _MAX_FILAS_VISIBLES = 8
    _ALTO_MINIMO = 56  # con 1 sola fila filtrada, igual se ve un cuadro con aire, no achicado

    def __init__(self, parent, values=None, command=None, height=40,
                 font=None, placeholder_text="", **kwargs):
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)

        self._valores = list(values or [])
        self._command = command
        self._popup = None
        self._ignorar_focusout = False
        self._pos_popup_al_abrir = None
        self._after_id_vigilar_scroll = None

        fuente = font or ctk.CTkFont(family=UI["fuente"], size=13)

        self.entry = ctk.CTkEntry(
            self, height=height, font=fuente,
            placeholder_text=placeholder_text,
            fg_color=UI["color_input_bg"], border_color=UI["color_border"],
            border_width=2, corner_radius=8,
        )
        self.entry.grid(row=0, column=0, sticky="ew")

        self.entry.bind("<KeyRelease>", self._on_tecla)
        self.entry.bind("<FocusIn>", lambda e: self._abrir())
        self.entry.bind("<FocusOut>", self._on_focus_out)
        self.entry.bind("<Return>", self._on_enter)
        self.entry.bind("<Escape>", lambda e: self._cerrar())

    def destroy(self):
        # Mismo criterio que el resto del proyecto con self.after() que
        # se reprograma solo (ver pesaje_entrada_view.py/pesaje_salida_view.py):
        # sin cancelarlo acá, al navegar a otra pantalla el timer de
        # _vigilar_scroll() sigue vivo referenciando un widget ya
        # destruido.
        if self._after_id_vigilar_scroll is not None:
            try:
                self.after_cancel(self._after_id_vigilar_scroll)
            except Exception:
                pass
            self._after_id_vigilar_scroll = None
        self._cerrar_popup_widget()
        super().destroy()

    # ---- API compatible con CTkComboBox ----
    def get(self) -> str:
        return self.entry.get()

    def set(self, valor: str):
        self.entry.delete(0, "end")
        self.entry.insert(0, valor)

    def configure(self, values=None, **kwargs):
        if values is not None:
            self._valores = list(values)

    # ---- Filtrado y popup ----
    def _on_tecla(self, event):
        if event.keysym in ("Return", "Escape", "Tab"):
            return  # manejados por sus propios binds
        self._abrir()

    def _valores_filtrados(self):
        texto = self.entry.get().strip().lower()
        if not texto:
            return self._valores
        return [v for v in self._valores if texto in v.lower()]

    def _abrir(self):
        self._construir_popup(self._valores_filtrados())

    def _construir_popup(self, filtrados):
        self._cerrar_popup_widget()

        if not filtrados or not self.entry.winfo_ismapped():
            return

        self._popup = ctk.CTkToplevel(self)
        self._popup.overrideredirect(True)
        self._popup.attributes("-topmost", True)
        # Sin esto, el popup por un instante aparece como ventana grande
        # en la esquina antes de reposicionarse -- se arma invisible y
        # se muestra recién ya en su lugar y tamaño finales.
        self._popup.withdraw()

        # winfo_rootx/rooty/width son píxeles FÍSICOS reales de pantalla.
        # CTkToplevel.geometry() escala automáticamente lo que se le pasa
        # (multiplica por el factor de escala de Windows), así que
        # pasarle píxeles físicos sin más los escalaba una SEGUNDA vez --
        # se probó primero deshaciendo la escala a mano
        # (_reverse_window_scaling) antes de llamar a .geometry(), pero
        # el resultado seguía mal (posición corrida) -- hay más de una
        # capa de escala mezclada acá (Tcl/Tk también tiene la suya) y
        # calcularla a mano a ciegas no es confiable.
        #
        # Más directo y sin ese problema: CTkToplevel solo sobreescribe
        # .geometry() -- .wm_geometry() (el nombre "de fábrica" de
        # Tkinter para exactamente lo mismo, Wm.geometry es un alias de
        # Wm.wm_geometry) NO está tocado, así que llama directo al Tcl
        # de abajo sin que CustomTkinter reescale nada. Con
        # wm_geometry() los píxeles físicos van tal cual, sin conversión.
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height() + 2
        self._pos_popup_al_abrir = (x, y)
        ancho = self.entry.winfo_width()
        alto = max(self._ALTO_MINIMO, min(len(filtrados), self._MAX_FILAS_VISIBLES) * self._ALTO_FILA + 8)

        # grid_propagate(False): sin esto, un texto largo en una fila
        # (ej. un nombre de producto largo) hace que Tk agrande la
        # ventana entera para que el contenido "entre", en vez de
        # respetar el ancho fijado en la geometría.
        self._popup.wm_geometry(f"{ancho}x{alto}+{x}+{y}")
        self._popup.grid_propagate(False)

        contenedor = ctk.CTkScrollableFrame(
            self._popup, fg_color=UI["color_card"],
            corner_radius=6, border_width=1, border_color=UI["color_border"],
        )
        contenedor.grid(row=0, column=0, sticky="nsew")
        self._popup.grid_columnconfigure(0, weight=1)
        self._popup.grid_rowconfigure(0, weight=1)
        contenedor.grid_columnconfigure(0, weight=1)
        ocultar_scrollbar(contenedor)
        # Nota: NO existe contenedor.grid_propagate(False) -- en
        # CTkScrollableFrame ese método está sobreescrito y no acepta el
        # argumento (tira TypeError, que Tkinter se traga en silencio
        # dentro de un callback y rompía el popup entero sin avisar en
        # pantalla). No hace falta: alcanza con el propagate del Toplevel
        # de arriba + el ancho ya truncado de cada fila, más abajo.

        # Ancho máximo de caracteres a mostrar por fila -- un texto más
        # largo que esto se trunca con "…" en vez de forzar el botón (y
        # con él, la ventana) más ancho que el campo.
        max_chars = max(8, ancho // 8)

        for valor in filtrados:
            texto = valor if len(valor) <= max_chars else valor[:max_chars - 1] + "…"
            ctk.CTkButton(
                contenedor, text=texto, anchor="w",
                height=self._ALTO_FILA - 4,
                fg_color="transparent", hover_color=UI["color_bg"],
                text_color=UI["color_text"],
                font=ctk.CTkFont(family=UI["fuente"], size=12),
                command=lambda v=valor: self._seleccionar(v),
            ).grid(sticky="ew", pady=1)

        self._popup.deiconify()
        self._vigilar_scroll()

    def _vigilar_scroll(self):
        """
        El popup es una ventana (Toplevel) aparte, posicionada una sola
        vez en coordenadas absolutas de pantalla -- si el usuario
        scrollea el formulario de atrás (ej. la tarjeta con scroll de
        Entrada de Camión), el campo se mueve pero el popup se queda
        clavado donde estaba, flotando sobre cualquier cosa que haya
        quedado debajo. Más simple y confiable que perseguir la posición
        real: si el campo se movió de donde estaba cuando se abrió el
        popup, se cierra solo -- mismo criterio que muchos buscadores
        web (el desplegable se cierra al scrollear la página).
        """
        if self._popup is None:
            self._after_id_vigilar_scroll = None
            return
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height() + 2
        if (x, y) != self._pos_popup_al_abrir:
            self._cerrar()
            return
        self._after_id_vigilar_scroll = self.after(100, self._vigilar_scroll)

    def _cerrar_popup_widget(self):
        if self._after_id_vigilar_scroll is not None:
            try:
                self.after_cancel(self._after_id_vigilar_scroll)
            except Exception:
                pass
            self._after_id_vigilar_scroll = None
        if self._popup is not None:
            try:
                self._popup.destroy()
            except Exception:
                pass
            self._popup = None

    def _cerrar(self):
        self._cerrar_popup_widget()

    def _on_focus_out(self, event):
        # El nuevo foco todavía no está resuelto en el mismo instante de
        # este evento (ej. si el usuario clickeó una fila del popup) --
        # se revisa con un pequeño delay en vez de cerrar de una.
        if self._ignorar_focusout:
            return
        self.after(120, self._cerrar_si_perdio_foco_de_verdad)

    def _cerrar_si_perdio_foco_de_verdad(self):
        try:
            foco = self.focus_get()
        except Exception:
            foco = None
        if foco is self.entry:
            return
        widget = foco
        while widget is not None:
            if widget == self._popup:
                return  # el foco sigue dentro del propio desplegable
            widget = getattr(widget, "master", None)
        self._cerrar()

    def _on_enter(self, event):
        self._cerrar()
        if self._command:
            self._command(self.entry.get())
        return "break"

    def _seleccionar(self, valor):
        # command de CTkButton corre en el mismo ciclo del clic --
        # cerrar y devolver el foco a la entrada ANTES de que el
        # FocusOut demorado de más arriba llegue a evaluarse.
        self._ignorar_focusout = True
        self.set(valor)
        self._cerrar()
        self.entry.focus_set()
        self.after(150, lambda: setattr(self, "_ignorar_focusout", False))
        if self._command:
            self._command(valor)
