# ============================================================
# gui/admin/configuracion_view.py — Configuración del sistema
# ============================================================

import customtkinter as ctk
from tkinter import messagebox
from database.engine import SessionLocal
from database.models import Configuracion
from config import EMPRESA, UI


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
        self._seccion(scroll, "⚖️ Báscula", row=6, col=0)
        params_bascula = [
            ("unidad_peso",   "Unidad de peso (KG, TN, LB)"),
            ("capacidad_max", "Capacidad máxima (KG)"),
        ]
        self._agregar_campos(scroll, params_bascula, row_start=7, col=0)

        # ---- Sección: Display ----
        self._seccion(scroll, "🖥️ Display de Pesaje", row=6, col=1)
        params_display = [
            ("puerto_com", "Puerto COM (ej: COM1)"),
            ("baudrate",   "Baudrate (ej: 9600)"),
        ]
        self._agregar_campos(scroll, params_display, row_start=7, col=1)

        # ---- Botón guardar ----
        ctk.CTkButton(
            scroll,
            text="💾 Guardar Configuración",
            command=self._guardar,
            height=48,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=UI["color_success"],
            hover_color=UI["color_success_hover"],
            corner_radius=10
        ).grid(row=12, column=0, columnspan=2, padx=10, pady=20, sticky="ew")

    def _seccion(self, parent, titulo, row, col):
        """Crea un header de sección."""
        ctk.CTkLabel(
            parent,
            text=titulo,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=UI["color_accent"]
        ).grid(row=row, column=col, padx=15, pady=(15, 5), sticky="w")

    def _agregar_campos(self, parent, params, row_start, col):
        """Crea campos de entrada para cada parámetro."""
        for i, (clave, etiqueta) in enumerate(params):
            frame = ctk.CTkFrame(
                parent,
                fg_color=UI["color_card"],
                border_color=UI["color_border"],
                border_width=1,
                corner_radius=8
            )
            frame.grid(row=row_start + i, column=col, padx=10, pady=4, sticky="ew")

            ctk.CTkLabel(
                frame, text=etiqueta,
                font=ctk.CTkFont(size=11),
                text_color=UI["color_muted"], anchor="w"
            ).pack(fill="x", padx=12, pady=(8, 2))

            entry = ctk.CTkEntry(frame, height=35, font=ctk.CTkFont(size=12))
            entry.pack(fill="x", padx=12, pady=(0, 8))

            self._campos[clave] = entry

    def _cargar_datos(self):
        """Carga los valores actuales desde la base de datos."""
        db = SessionLocal()
        try:
            for clave, entry in self._campos.items():
                cfg = db.query(Configuracion).filter_by(clave=clave).first()
                entry.delete(0, "end")
                if cfg:
                    entry.insert(0, cfg.valor or "")
        finally:
            db.close()

    def _guardar(self):
        """Guarda todos los valores en la base de datos."""
        db = SessionLocal()
        try:
            for clave, entry in self._campos.items():
                valor = entry.get().strip()
                cfg = db.query(Configuracion).filter_by(clave=clave).first()
                if cfg:
                    cfg.valor = valor
                else:
                    db.add(Configuracion(clave=clave, valor=valor))
            db.commit()
            messagebox.showinfo(
                "✅ Configuración Guardada",
                "Los cambios han sido guardados.\n\n"
                "Algunos cambios (como el nombre de empresa) se verán\n"
                "en los próximos tickets y reportes generados."
            )
        except Exception as e:
            db.rollback()
            messagebox.showerror("Error", f"No se pudo guardar: {e}")
        finally:
            db.close()
