# ============================================================
# gui/pesaje/completar_pesaje_view.py
# ============================================================
# Vista para que Romana complete los datos finales DESPUÉS
# de que Centro de Costos haya aprobado la pesada.

import customtkinter as ctk
from tkinter import messagebox, ttk
from datetime import datetime
from config import UI, REPORTS_DIR
from client.api_client import api_client, ApiError
from gui.async_utils import cargar_en_hilo
import os


def _hora(iso_str):
    """La API devuelve fechas como texto ISO 8601 — se parsean para mostrar solo HH:MM."""
    if not iso_str:
        return "—"
    return datetime.fromisoformat(iso_str).strftime("%H:%M")


class CompletarPesajeView(ctk.CTkFrame):
    """
    Pantalla para completar pesadas aprobadas por CC.

    FLUJO:
      CC aprobó → estado 'aprobado'
      Romana abre esta pantalla, llena datos finales
      → estado 'completado', genera ticket PDF
    """

    def __init__(self, parent, callback_navegar=None):
        super().__init__(parent, fg_color="transparent")
        self.callback_navegar = callback_navegar
        self._pesada_seleccionada = None
        self._construir()
        self._cargar_lista()

    # ----------------------------------------------------------
    def _construir(self):
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        self._construir_lista()
        self._construir_formulario()

    # ----------------------------------------------------------
    def _construir_lista(self):
        frame = ctk.CTkFrame(self, fg_color=UI["color_card"],
                              border_color=UI["color_border"],
                              border_width=1, corner_radius=12)
        frame.grid(row=0, column=0, sticky="nsew",
                   padx=(20, 8), pady=20)
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew",
                     padx=16, pady=(16, 4))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="✅  APROBADAS POR CC — PENDIENTES DE COMPLETAR",
            font=ctk.CTkFont(family=UI["fuente"], size=13, weight="bold"),
            text_color=UI["color_success"]
        ).grid(row=0, column=0, sticky="w")

        self._lbl_count = ctk.CTkLabel(
            header, text="0 pendientes",
            font=ctk.CTkFont(family=UI["fuente"], size=11),
            text_color=UI["color_muted"]
        )
        self._lbl_count.grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(
            frame,
            text="Seleccione la pesada aprobada y complete los datos finales.",
            font=ctk.CTkFont(family=UI["fuente"], size=11),
            text_color=UI["color_muted"]
        ).grid(row=1, column=0, padx=16, pady=(0, 8), sticky="w")

        # Tabla
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Completar.Treeview",
            background="#ffffff",
            foreground="#1e293b",
            fieldbackground="#f8fafc",
            rowheight=32,
            font=("Segoe UI", 11)
        )
        style.configure("Completar.Treeview.Heading",
            background="#f0fdf4",
            foreground="#166534",
            font=("Segoe UI", 10, "bold")
        )
        style.map("Completar.Treeview",
            background=[("selected", "#dcfce7")],
            foreground=[("selected", "#14532d")]
        )

        cols = ("ticket", "placa", "producto", "neto", "aprobado_por", "hora")
        self._tree = ttk.Treeview(frame, columns=cols, show="headings",
                                   style="Completar.Treeview",
                                   selectmode="browse")

        configs = [
            ("ticket",      "TICKET",      110),
            ("placa",       "PLACA",        80),
            ("producto",    "PRODUCTO",    140),
            ("neto",        "NETO KG",      90),
            ("aprobado_por","APROBADO POR", 120),
            ("hora",        "HORA APROB.",   90),
        ]
        for col, titulo, ancho in configs:
            self._tree.heading(col, text=titulo)
            self._tree.column(col, width=ancho, minwidth=60)

        scroll = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll.set)
        self._tree.grid(row=2, column=0, sticky="nsew", padx=(10, 0))
        scroll.grid(row=2, column=1, sticky="ns")
        self._tree.bind("<<TreeviewSelect>>", self._on_seleccion)

        ctk.CTkButton(
            frame, text="↻  Actualizar",
            command=self._cargar_lista,
            height=30, width=120,
            fg_color="transparent",
            border_color=UI["color_border"], border_width=1,
            text_color=UI["color_text"],
            hover_color=UI["color_bg"],
            font=ctk.CTkFont(family=UI["fuente"], size=11)
        ).grid(row=3, column=0, padx=10, pady=(6, 12), sticky="w")

    # ----------------------------------------------------------
    def _construir_formulario(self):
        """Panel derecho — datos finales a completar."""
        self._panel = ctk.CTkFrame(self, fg_color=UI["color_card"],
                                    border_color=UI["color_border"],
                                    border_width=1, corner_radius=12)
        self._panel.grid(row=0, column=1, sticky="nsew",
                          padx=(8, 20), pady=20)
        self._panel.grid_columnconfigure(0, weight=1)

        self._lbl_placeholder = ctk.CTkLabel(
            self._panel,
            text="← Seleccione una pesada\naprobada para completarla",
            font=ctk.CTkFont(family=UI["fuente"], size=14),
            text_color=UI["color_muted"],
            justify="center"
        )
        self._lbl_placeholder.grid(row=0, column=0, padx=20, pady=60)

        self._form_frame = ctk.CTkFrame(self._panel, fg_color="transparent")

    # ----------------------------------------------------------
    def _cargar_lista(self):
        for item in self._tree.get_children():
            self._tree.delete(item)

        cargar_en_hilo(
            self, api_client.listar_aprobadas_pendientes,
            on_exito=self._poblar_lista,
            on_error=lambda e: messagebox.showerror("Error de conexión", str(e)),
        )

    def _poblar_lista(self, pesadas):
        for p in pesadas:
            aprobado_por = (p["aprobado_por"]["nombre_completo"][:16]
                            if p["aprobado_por"] else "CC")
            self._tree.insert("", "end", iid=str(p["id"]), values=(
                p["numero_ticket"],
                p["vehiculo"]["placa"] if p["vehiculo"] else "—",
                (p["producto"]["nombre"][:16] if p["producto"] else "—"),
                f"{float(p['peso_neto'] or 0):,.0f}",
                aprobado_por,
                _hora(p["fecha_aprobacion"])
            ))

        self._lbl_count.configure(text=f"{len(pesadas)} pendiente(s)")
        self._pesada_seleccionada = None
        self._limpiar_form()

    # ----------------------------------------------------------
    def _on_seleccion(self, event):
        sel = self._tree.selection()
        if not sel:
            return

        pesada_id = int(sel[0])
        try:
            p = api_client.obtener_pesada(pesada_id)
        except ApiError as e:
            messagebox.showerror("Error de conexión", str(e))
            return

        if p:
            self._pesada_seleccionada = p
            self._mostrar_formulario(p)

    # ----------------------------------------------------------
    def _mostrar_formulario(self, p):
        self._lbl_placeholder.grid_forget()
        self._form_frame.grid(row=0, column=0, sticky="nsew",
                               padx=16, pady=16)
        self._form_frame.grid_columnconfigure(0, weight=1)

        for w in self._form_frame.winfo_children():
            w.destroy()

        row = 0

        # Resumen de la pesada
        ctk.CTkLabel(
            self._form_frame,
            text=f"Ticket {p['numero_ticket']}",
            font=ctk.CTkFont(family=UI["fuente"], size=15, weight="bold"),
            text_color=UI["color_success"]
        ).grid(row=row, column=0, sticky="w", pady=(0, 2)); row += 1

        ctk.CTkLabel(
            self._form_frame,
            text=f"✅ Aprobado por Centro de Costos",
            font=ctk.CTkFont(family=UI["fuente"], size=11),
            text_color=UI["color_success"]
        ).grid(row=row, column=0, sticky="w", pady=(0, 6)); row += 1

        # Datos ya registrados (solo lectura)
        info_frame = ctk.CTkFrame(self._form_frame, fg_color=UI["color_bg"],
                                   corner_radius=8)
        info_frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        info_frame.grid_columnconfigure((0, 1, 2), weight=1)
        row += 1

        self._dato_rapido(info_frame, 0, "ENTRADA",
            f"{float(p['peso_bruto'] or 0):,.0f} KG", UI["color_muted"])
        self._dato_rapido(info_frame, 1, "SALIDA",
            f"{float(p['peso_tara'] or 0):,.0f} KG", "#f59e0b")
        self._dato_rapido(info_frame, 2, "NETO",
            f"{float(p['peso_neto'] or 0):,.0f} KG", UI["color_success"])

        # Separador
        ctk.CTkFrame(self._form_frame, height=1,
                      fg_color=UI["color_border"]).grid(
            row=row, column=0, sticky="ew", pady=10); row += 1

        ctk.CTkLabel(
            self._form_frame,
            text="COMPLETE LOS DATOS FINALES",
            font=ctk.CTkFont(family=UI["fuente"], size=10, weight="bold"),
            text_color=UI["color_muted"]
        ).grid(row=row, column=0, sticky="w", pady=(0, 8)); row += 1

        # Campos finales
        self._entry_orden_compra = self._campo(
            self._form_frame, row, "N° Guía / Orden de Compra:",
            "Ingrese número de orden o guía (opcional)"
        ); row += 2

        self._entry_cantidad = self._campo(
            self._form_frame, row, "Cantidad:",
            "Cantidad en unidades (opcional)"
        ); row += 2

        self._entry_precintos = self._campo(
            self._form_frame, row, "Precintos:",
            "Número(s) de precinto(s) (opcional)"
        ); row += 2

        ctk.CTkLabel(
            self._form_frame, text="Observaciones:",
            font=ctk.CTkFont(family=UI["fuente"], size=11),
            text_color=UI["color_muted"]
        ).grid(row=row, column=0, sticky="w", pady=(4, 2)); row += 1

        self._txt_obs = ctk.CTkTextbox(
            self._form_frame, height=70,
            font=ctk.CTkFont(family=UI["fuente"], size=12)
        )
        self._txt_obs.grid(row=row, column=0, sticky="ew", pady=(0, 10)); row += 1

        # Botón completar
        ctk.CTkButton(
            self._form_frame,
            text="💾  GUARDAR Y COMPLETAR",
            command=self._completar,
            height=50,
            font=ctk.CTkFont(family=UI["fuente"], size=14, weight="bold"),
            fg_color=UI["color_accent"],
            hover_color=UI["color_accent_hover"],
            corner_radius=8
        ).grid(row=row, column=0, sticky="ew"); row += 1

    # ----------------------------------------------------------
    def _campo(self, parent, row, label, placeholder):
        ctk.CTkLabel(
            parent, text=label,
            font=ctk.CTkFont(family=UI["fuente"], size=11),
            text_color=UI["color_muted"]
        ).grid(row=row, column=0, sticky="w", pady=(4, 2))

        entry = ctk.CTkEntry(
            parent, placeholder_text=placeholder,
            height=34, font=ctk.CTkFont(family=UI["fuente"], size=12)
        )
        entry.grid(row=row + 1, column=0, sticky="ew", pady=(0, 4))
        return entry

    # ----------------------------------------------------------
    def _dato_rapido(self, parent, col, label, valor, color):
        ctk.CTkLabel(
            parent, text=label,
            font=ctk.CTkFont(family=UI["fuente"], size=9, weight="bold"),
            text_color=UI["color_muted"]
        ).grid(row=0, column=col, padx=6, pady=(8, 2))

        ctk.CTkLabel(
            parent, text=valor,
            font=ctk.CTkFont(family=UI["fuente"], size=14, weight="bold"),
            text_color=color
        ).grid(row=1, column=col, padx=6, pady=(0, 8))

    # ----------------------------------------------------------
    def _completar(self):
        if not self._pesada_seleccionada:
            return

        orden = self._entry_orden_compra.get().strip()
        cantidad_str = self._entry_cantidad.get().strip()
        precintos = self._entry_precintos.get().strip()
        obs = self._txt_obs.get("1.0", "end").strip()

        cantidad = None
        if cantidad_str:
            try:
                cantidad = float(cantidad_str.replace(",", "."))
            except ValueError:
                messagebox.showerror("Validación",
                    "La cantidad debe ser un número válido.")
                return

        resultado = api_client.completar_pesaje(
            pesada_id=self._pesada_seleccionada["id"],
            orden_compra=orden,
            cantidad=cantidad,
            precintos=precintos,
            observaciones=obs
        )

        if resultado["exito"]:
            pesada = resultado["pesada"]
            # Generar ticket PDF — el servidor lo genera (Romana y Centro de
            # Costos no comparten disco) y acá se guarda localmente para abrirlo.
            try:
                pdf_bytes = api_client.descargar_ticket_pdf(pesada["id"])
                os.makedirs(REPORTS_DIR, exist_ok=True)
                ruta_pdf = os.path.join(REPORTS_DIR, f"TICKET_{pesada['numero_ticket']}.pdf")
                with open(ruta_pdf, "wb") as f:
                    f.write(pdf_bytes)
                if messagebox.askyesno(
                    "Completado ✓",
                    f"Pesada {pesada['numero_ticket']} completada.\n"
                    f"Neto: {float(pesada['peso_neto'] or 0):,.0f} KG\n\n"
                    "¿Abrir el ticket PDF?"
                ):
                    os.startfile(ruta_pdf)
            except (ApiError, OSError):
                messagebox.showinfo(
                    "Completado ✓",
                    f"Pesada {pesada['numero_ticket']} completada.\n"
                    f"Neto: {float(pesada['peso_neto'] or 0):,.0f} KG"
                )
            self._cargar_lista()
        else:
            messagebox.showerror("Error", resultado["mensaje"])

    # ----------------------------------------------------------
    def _limpiar_form(self):
        for w in self._form_frame.winfo_children():
            w.destroy()
        self._form_frame.grid_forget()
        self._lbl_placeholder.grid(row=0, column=0, padx=20, pady=60)
