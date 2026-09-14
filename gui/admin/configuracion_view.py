# ============================================================
# gui/admin/configuracion_view.py — Configuración del sistema
# ============================================================

import customtkinter as ctk
from tkinter import messagebox
from client.api_client import api_client, ApiError
from config import EMPRESA, UI
from gui.async_utils import cargar_en_hilo
from gui.components.ui_kit import Card, titulo_h2, etiqueta_campo, boton_primario


class ConfiguracionView(ctk.CTkFrame):
    """
    Pantalla de configuración del sistema.
    Permite cambiar los parámetros de la empresa, báscula y display.
    """

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._campos = {}  # clave → widget Entry
        self._construir()
        self._cargar_datos()

    def _construir(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Scroll general
        scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", label_text="")
        scroll.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        scroll.grid_columnconfigure(0, weight=1)
        scroll.grid_columnconfigure(1, weight=1)

        # ---- Sección: Datos de la empresa ----
        self._seccion(scroll, "🏢 Datos de la Empresa", row=0, col=0)
        params_empresa = [
            ("nombre_empresa",    "Nombre / Razón Social"),
            ("rif_empresa",       "RIF / NIT / RFC"),
            ("direccion_empresa", "Dirección"),
            ("telefono_empresa",  "Teléfono"),
        ]
        self._agregar_campos(scroll, params_empresa, row_start=1, col=0)

        # ---- Sección: Numeración ----
        self._seccion(scroll, "🎫 Numeración", row=0, col=1)
        params_num = [
            ("prefijo_ticket", "Prefijo del ticket (ej: TK)"),
            ("ticket_actual",  "Número de ticket actual"),
            ("corte_actual",   "Número de corte actual"),
        ]
        self._agregar_campos(scroll, params_num, row_start=1, col=1)

        # ---- Sección: Báscula ----
        self._seccion(scroll, "⚖ Báscula", row=6, col=0)
        params_bascula = [
            ("unidad_peso",   "Unidad de peso (KG, TN, LB)"),
            ("capacidad_max", "Capacidad máxima (KG)"),
        ]
        self._agregar_campos(scroll, params_bascula, row_start=7, col=0)

        # ---- Sección: Display ----
        self._seccion(scroll, "🖥 Display de Pesaje", row=6, col=1)
        params_display = [
            ("puerto_com", "Puerto COM (ej: COM1)"),
            ("baudrate",   "Baudrate (ej: 9600)"),
        ]
        self._agregar_campos(scroll, params_display, row_start=7, col=1)

        # ---- Botón guardar ----
        boton_primario(
            scroll, "💾 Guardar Configuración", command=self._guardar, height=48,
        ).grid(row=12, column=0, columnspan=2, padx=10, pady=20, sticky="ew")

    def _seccion(self, parent, titulo, row, col):
        """Crea un header de sección."""
        titulo_h2(parent, titulo).grid(row=row, column=col, padx=15, pady=(15, 5), sticky="w")

    def _agregar_campos(self, parent, params, row_start, col):
        """Crea campos de entrada para cada parámetro."""
        for i, (clave, etiqueta) in enumerate(params):
            frame = Card(parent)
            frame.grid(row=row_start + i, column=col, padx=10, pady=4, sticky="ew")

            etiqueta_campo(frame, etiqueta, anchor="w").pack(fill="x", padx=12, pady=(8, 2))

            entry = ctk.CTkEntry(frame, height=35, font=ctk.CTkFont(family=UI["fuente"], size=12))
            entry.pack(fill="x", padx=12, pady=(0, 8))

            self._campos[clave] = entry

    def _cargar_datos(self):
        """Carga los valores actuales desde el servidor."""
        cargar_en_hilo(
            self, api_client.listar_configuracion,
            on_exito=lambda lista: self._poblar_campos({c["clave"]: c["valor"] for c in lista}),
            on_error=lambda e: messagebox.showerror("Error de conexión", str(e)),
        )

    def _poblar_campos(self, configuraciones):
        for clave, entry in self._campos.items():
            entry.delete(0, "end")
            entry.insert(0, configuraciones.get(clave) or "")

    def _guardar(self):
        """Guarda todos los valores en el servidor (upsert por clave)."""
        for clave, entry in self._campos.items():
            resultado = api_client.actualizar_configuracion(clave, entry.get().strip())
            if not resultado["exito"]:
                messagebox.showerror("Error", f"No se pudo guardar '{clave}': {resultado['mensaje']}")
                return
        messagebox.showinfo(
            "✅ Configuración Guardada",
            "Los cambios han sido guardados.\n\n"
            "Algunos cambios (como el nombre de empresa) se verán\n"
            "en los próximos tickets y reportes generados."
        )
