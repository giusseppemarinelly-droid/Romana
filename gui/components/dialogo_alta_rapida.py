# ============================================================
# gui/components/dialogo_alta_rapida.py — Alta rápida de un maestro
# ============================================================
# Modal genérico para dar de alta un Vehículo/Conductor/Transportista/
# Proveedor SIN salir de la pantalla donde se lo está buscando (ej.
# Entrada de Camión) -- antes, si la placa/cédula/código no existía, el
# operador tenía que anotarlo, ir a Maestros, cargarlo ahí, y volver a
# Entrada a terminar el pesaje. Con permiso "maestros_crear" (niveles
# 1-2-3 desde 2026-09-17, Romana incluida) esto ya no hace falta.
#
# A propósito solo pide los campos esenciales, no el formulario
# completo de Maestros (ej. Proveedor no pide RIF/dirección/email acá)
# -- es "alta rápida" para no frenar el pesaje; los datos que falten se
# completan después en Maestros con calma, si hace falta.

import os
import customtkinter as ctk
from tkinter import messagebox
from config import UI
from client.api_client import api_client
from gui.components.ui_kit import boton_primario, boton_secundario, titulo_h2, etiqueta_campo, texto_ayuda

_ICONO_VENTANA = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "assets", "icono.ico"
)


class DialogoAltaRapida(ctk.CTkToplevel):
    """
    Uso:
        DialogoAltaRapida(
            self, titulo="Nuevo vehículo", subtitulo="...", recurso="vehiculos",
            campos=[("placa", "Placa", True), ("descripcion", "Descripción", False), ...],
            valores_iniciales={"placa": "ABC-123"},
            on_creado=lambda registro: ...,
        )
    El diálogo se cierra solo si el alta sale bien; si falla (placa
    duplicada, campo requerido vacío, etc.) se queda abierto mostrando
    el error para corregir sin perder lo ya tipeado.
    """

    def __init__(self, parent, titulo, recurso, campos, on_creado,
                 valores_iniciales=None, subtitulo="Alta rápida — sin salir de esta pantalla"):
        super().__init__(parent)
        # Se arma invisible y recién se muestra ya centrado y en su
        # tamaño final -- mismo criterio que el popup de
        # gui/components/combo_buscable.py: sin esto, por un instante
        # se ve la ventana en la esquina en un tamaño provisorio antes
        # de reposicionarse, que es justo lo que se veía mal.
        self.withdraw()
        self.title(titulo)
        try:
            self.iconbitmap(_ICONO_VENTANA)
        except Exception:
            pass

        self._recurso = recurso
        self._campos = campos
        self._on_creado = on_creado
        self._entries = {}

        self.configure(fg_color=UI["color_bg"])
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.grab_set()  # modal -- no se puede tocar la pantalla de atrás sin cerrarlo

        self.grid_columnconfigure(0, weight=1)

        # Card con franja de acento -- mismo lenguaje visual que la
        # card de login (gui/login_view.py), no un formulario suelto.
        card = ctk.CTkFrame(
            self, fg_color=UI["color_card"], corner_radius=UI["radio_card"],
            border_width=1, border_color=UI["color_border"],
        )
        card.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)

        stripe = ctk.CTkFrame(card, fg_color=UI["color_accent"], height=4, corner_radius=2)
        stripe.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 0))

        titulo_h2(card, titulo).grid(row=1, column=0, padx=24, pady=(14, 0), sticky="w")
        if subtitulo:
            texto_ayuda(card, subtitulo).grid(row=2, column=0, padx=24, pady=(2, 4), sticky="w")

        valores_iniciales = valores_iniciales or {}
        fila = 3
        for clave, etiqueta, requerido in campos:
            texto_etiqueta = etiqueta + (" *" if requerido else "")
            etiqueta_campo(card, texto_etiqueta).grid(
                row=fila, column=0, padx=24, pady=(14, 4), sticky="w")
            fila += 1

            entry = ctk.CTkEntry(
                card, height=40, width=320,
                font=ctk.CTkFont(family=UI["fuente"], size=13),
                fg_color=UI["color_input_bg"], border_color=UI["color_border"],
                border_width=2, corner_radius=UI["radio_control"],
            )
            entry.grid(row=fila, column=0, padx=24, sticky="ew")
            if clave in valores_iniciales and valores_iniciales[clave]:
                entry.insert(0, str(valores_iniciales[clave]))
            self._entries[clave] = entry
            fila += 1

        botones = ctk.CTkFrame(card, fg_color="transparent")
        botones.grid(row=fila, column=0, padx=24, pady=(20, 24), sticky="ew")
        botones.grid_columnconfigure((0, 1), weight=1)

        boton_secundario(botones, "Cancelar", command=self.destroy).grid(
            row=0, column=0, padx=(0, 6), sticky="ew")
        boton_primario(botones, "Guardar", command=self._guardar).grid(
            row=0, column=1, padx=(6, 0), sticky="ew")

        # Foco en el primer campo vacío (si el que abrió el diálogo ya
        # vino con la placa/cédula/código tipeados, arrancar ahí es
        # más molesto que arrancar en el siguiente campo vacío).
        for clave, entry in self._entries.items():
            if not entry.get().strip():
                entry.focus_set()
                break

        self._centrar_sobre_padre(parent)
        self.deiconify()
        self.after(50, lambda: self.focus_force())

    def _centrar_sobre_padre(self, parent):
        """
        Centra el diálogo sobre la ventana principal, no sobre la
        pantalla entera -- con dos monitores o la app no maximizada,
        centrar en pantalla puede dejarlo lejos de donde el operador
        está mirando.

        winfo_reqwidth/reqheight ya son píxeles físicos reales (Tk los
        calcula después de que CTk aplicó su propio escalado al
        construir cada widget) -- por eso acá también se usa
        wm_geometry() en vez de geometry(): esta última reescala lo
        que se le pasa una segunda vez (mismo hallazgo que el popup de
        combo_buscable.py), y con medidas ya físicas eso descuadra la
        ventana.
        """
        self.update_idletasks()
        ancho = self.winfo_reqwidth()
        alto = self.winfo_reqheight()

        raiz = parent.winfo_toplevel()
        px = raiz.winfo_rootx() + (raiz.winfo_width() - ancho) // 2
        py = raiz.winfo_rooty() + (raiz.winfo_height() - alto) // 2
        self.wm_geometry(f"{ancho}x{alto}+{max(px, 0)}+{max(py, 0)}")

    def _guardar(self):
        datos = {}
        for clave, etiqueta, requerido in self._campos:
            valor = self._entries[clave].get().strip()
            if requerido and not valor:
                messagebox.showwarning("Falta un dato", f"'{etiqueta}' es obligatorio.", parent=self)
                self._entries[clave].focus_set()
                return
            datos[clave] = valor or None

        resultado = api_client.crear_maestro(self._recurso, datos)
        if not resultado["exito"]:
            messagebox.showerror("No se pudo guardar", resultado["mensaje"], parent=self)
            return

        self.destroy()
        self._on_creado(resultado["data"])
