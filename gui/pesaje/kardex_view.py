# ============================================================
# gui/pesaje/kardex_view.py — Kardex de Pesadas
# ============================================================

import customtkinter as ctk
from tkinter import messagebox, ttk
from datetime import datetime, timedelta
from client.api_client import api_client, ApiError
import os
from config import UI, REPORTS_DIR
from gui.async_utils import cargar_en_hilo

# Mapea la etiqueta legible del combo al valor real de Pesada.estado.
# (antes de esta migración el combo usaba "Completada"/"Pendiente"/"Anulada"
# en minúscula, que nunca coincidía con los estados reales del modelo
# "completado"/"pendiente_aprobacion"/"anulado" — el filtro nunca funcionó)
ESTADOS = {
    "Todos": None,
    "En planta": "en_planta",
    "Pendiente aprobación": "pendiente_aprobacion",
    "Aprobada": "aprobado",
    "Rechazada": "rechazado",
    "Completada": "completado",
    "Anulada": "anulado",
}


def _fecha_hora(iso_str):
    if not iso_str:
        return "—"
    return datetime.fromisoformat(iso_str).strftime("%d/%m/%Y %H:%M")


class KardexView(ctk.CTkFrame):
    """Pantalla de consulta del historial de pesadas (Kardex)."""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._pesadas = []
        self._construir()
        self._buscar()

    def _construir(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ---- Barra de filtros ----
        filtros = ctk.CTkFrame(
            self,
            fg_color=UI["color_card"],
            border_color=UI["color_border"],
            border_width=1,
            corner_radius=10
        )
        filtros.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))

        ctk.CTkLabel(
            filtros, text="📋 KARDEX DE PESADAS",
            font=ctk.CTkFont(family=UI["fuente"], size=15, weight="bold"),
            text_color=UI["color_accent"]
        ).grid(row=0, column=0, padx=15, pady=(12, 5), sticky="w", columnspan=8)

        # Fechas
        ctk.CTkLabel(filtros, text="Desde:", font=ctk.CTkFont(family=UI["fuente"], size=11),
                     text_color=UI["color_text"]).grid(row=1, column=0, padx=(15, 2), pady=10)

        hoy = datetime.now()
        inicio = hoy - timedelta(days=30)

        self._entry_desde = ctk.CTkEntry(filtros, width=110, height=32,
                                          placeholder_text="dd/mm/aaaa")
        self._entry_desde.grid(row=1, column=1, padx=(0, 10))
        self._entry_desde.insert(0, inicio.strftime("%d/%m/%Y"))

        ctk.CTkLabel(filtros, text="Hasta:", font=ctk.CTkFont(family=UI["fuente"], size=11),
                     text_color=UI["color_text"]).grid(row=1, column=2, padx=(0, 2))

        self._entry_hasta = ctk.CTkEntry(filtros, width=110, height=32,
                                          placeholder_text="dd/mm/aaaa")
        self._entry_hasta.grid(row=1, column=3, padx=(0, 10))
        self._entry_hasta.insert(0, hoy.strftime("%d/%m/%Y"))

        # Estado
        ctk.CTkLabel(filtros, text="Estado:", font=ctk.CTkFont(family=UI["fuente"], size=11),
                     text_color=UI["color_text"]).grid(row=1, column=4, padx=(0, 2))

        self._combo_estado = ctk.CTkComboBox(
            filtros, values=list(ESTADOS.keys()),
            width=150, height=32)
        self._combo_estado.grid(row=1, column=5, padx=(0, 10))
        self._combo_estado.set("Todos")

        # Botones
        ctk.CTkButton(
            filtros, text="🔍 Buscar", command=self._buscar,
            height=32, width=100, fg_color=UI["color_accent"], hover_color=UI["color_accent_hover"]
        ).grid(row=1, column=6, padx=(0, 5))

        # Atajo del reporte de fin de día: pone Desde=Hasta=hoy y filtra
        # directo, en vez de que el operador tenga que escribir la fecha
        # a mano para ver "todos los camiones que pasaron hoy".
        ctk.CTkButton(
            filtros, text="📅 Hoy", command=self._filtrar_hoy,
            height=32, width=80, fg_color="transparent",
            border_color=UI["color_accent"], border_width=1,
            text_color=UI["color_accent"], hover_color=UI["color_bg"],
            font=ctk.CTkFont(family=UI["fuente"], size=12)
        ).grid(row=1, column=7, padx=(0, 5))

        # Exportar (PDF/Excel) requiere "reportes_exportar" — el backend
        # ya lo exige; acá se oculta el botón en vez de dejar que el
        # usuario se tope con un error 403 al hacer clic.
        if api_client.tiene_permiso("reportes_exportar"):
            ctk.CTkButton(
                filtros, text="PDF", command=self._exportar_pdf,
                height=32, width=70, fg_color=UI["color_danger"], hover_color=UI["color_danger_hover"]
            ).grid(row=1, column=8, padx=(0, 5))

            ctk.CTkButton(
                filtros, text="Excel", command=self._exportar_excel,
                height=32, width=80, fg_color=UI["color_success"], hover_color=UI["color_success_hover"]
            ).grid(row=1, column=9, padx=(0, 15), pady=10)

        # ---- Tabla de resultados ----
        tabla_frame = ctk.CTkFrame(
            self,
            fg_color=UI["color_card"],
            border_color=UI["color_border"],
            border_width=1,
            corner_radius=10
        )
        tabla_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(5, 15))
        tabla_frame.grid_rowconfigure(1, weight=1)
        tabla_frame.grid_columnconfigure(0, weight=1)

        # Etiqueta de conteo + botón de ticket individual
        header_tabla = ctk.CTkFrame(tabla_frame, fg_color="transparent")
        header_tabla.grid(row=0, column=0, columnspan=2, sticky="ew", padx=15, pady=(10, 5))
        header_tabla.grid_columnconfigure(0, weight=1)

        self._lbl_count = ctk.CTkLabel(
            header_tabla, text="0 registros",
            font=ctk.CTkFont(family=UI["fuente"], size=11), text_color=UI["color_muted"]
        )
        self._lbl_count.grid(row=0, column=0, sticky="w")

        # Ver/descargar el ticket de una pesada puntual (no todo el
        # kardex) -- antes solo se podía exportar la lista completa en
        # PDF/Excel, no bajar el ticket de un camión específico.
        ctk.CTkButton(
            header_tabla, text="🎫 Ver Ticket", command=self._ver_ticket,
            height=28, width=110, fg_color=UI["color_accent"],
            hover_color=UI["color_accent_hover"],
            font=ctk.CTkFont(family=UI["fuente"], size=11)
        ).grid(row=0, column=1, sticky="e")

        # Tabla (usando ttk.Treeview que funciona dentro de tkinter)
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Kardex.Treeview",
            background=UI["color_card"],
            foreground=UI["color_text"],
            fieldbackground=UI["color_card"],
            rowheight=28,
            font=("Segoe UI", 11)
        )
        style.configure("Kardex.Treeview.Heading",
            background=UI["color_bg"],
            foreground=UI["color_text"],
            font=("Segoe UI", 10, "bold")
        )
        style.map("Kardex.Treeview",
            background=[("selected", "#E0F2FE")],
            foreground=[("selected", "#1E3A8A")])

        columnas = ("ticket", "fecha", "placa", "conductor",
                    "producto", "bruto", "tara", "neto", "estado")
        self._tree = ttk.Treeview(
            tabla_frame,
            columns=columnas,
            show="headings",
            style="Kardex.Treeview"
        )

        # Configurar columnas
        configs = [
            ("ticket",    "TICKET",      110),
            ("fecha",     "FECHA",       140),
            ("placa",     "PLACA",        80),
            ("conductor", "CONDUCTOR",   140),
            ("producto",  "PRODUCTO",    140),
            ("bruto",     "BRUTO KG",    100),
            ("tara",      "TARA KG",     100),
            ("neto",      "NETO KG",     100),
            ("estado",    "ESTADO",       90),
        ]
        for col_id, titulo, ancho in configs:
            self._tree.heading(col_id, text=titulo)
            self._tree.column(col_id, width=ancho, minwidth=60)

        # Scrollbar
        scroll_y = ttk.Scrollbar(tabla_frame, orient="vertical",
                                   command=self._tree.yview)
        scroll_x = ttk.Scrollbar(tabla_frame, orient="horizontal",
                                   command=self._tree.xview)
        self._tree.configure(yscrollcommand=scroll_y.set,
                              xscrollcommand=scroll_x.set)

        self._tree.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=(0, 0))
        scroll_y.grid(row=1, column=1, sticky="ns")
        scroll_x.grid(row=2, column=0, sticky="ew", padx=(10, 0))

        # Etiqueta de totales
        self._lbl_total = ctk.CTkLabel(
            tabla_frame, text="Total Neto: 0.00 KG",
            font=ctk.CTkFont(family=UI["fuente"], size=12, weight="bold"),
            text_color=UI["color_success"]
        )
        self._lbl_total.grid(row=3, column=0, padx=15, pady=10, sticky="e")

    def _filtrar_hoy(self):
        """Pone Desde y Hasta en la fecha de hoy y busca — reporte del día."""
        hoy_str = datetime.now().strftime("%d/%m/%Y")
        self._entry_desde.delete(0, "end")
        self._entry_desde.insert(0, hoy_str)
        self._entry_hasta.delete(0, "end")
        self._entry_hasta.insert(0, hoy_str)
        self._buscar()

    def _buscar(self):
        """Ejecuta la búsqueda con los filtros actuales."""
        # Parsear fechas
        try:
            desde_str = self._entry_desde.get().strip()
            hasta_str = self._entry_hasta.get().strip()
            fecha_inicio = datetime.strptime(desde_str, "%d/%m/%Y") if desde_str else None
            fecha_fin = datetime.strptime(hasta_str, "%d/%m/%Y").replace(
                hour=23, minute=59, second=59) if hasta_str else None
        except ValueError:
            messagebox.showerror("Error", "Formato de fecha incorrecto. Use dd/mm/aaaa")
            return

        estado = ESTADOS.get(self._combo_estado.get())

        # Se guardan los filtros tal cual se los pasamos a la API para
        # poder reusarlos en _exportar_pdf/_exportar_excel sin duplicar
        # el parseo de fechas.
        self._filtros_actuales = {
            "fecha_inicio": fecha_inicio.isoformat() if fecha_inicio else None,
            "fecha_fin": fecha_fin.isoformat() if fecha_fin else None,
            "estado": estado,
        }

        cargar_en_hilo(
            self, lambda: api_client.get_kardex(**self._filtros_actuales),
            on_exito=self._poblar_resultados,
            on_error=lambda e: messagebox.showerror("Error de conexión", str(e)),
        )

    def _poblar_resultados(self, pesadas):
        self._pesadas = pesadas

        # Limpiar tabla
        for item in self._tree.get_children():
            self._tree.delete(item)

        # Poblar tabla
        total_neto = 0.0
        for i, p in enumerate(self._pesadas):
            neto = float(p["peso_neto"] or 0)
            total_neto += neto

            tag = "par" if i % 2 == 0 else "impar"
            self._tree.insert("", "end", iid=str(p["id"]), values=(
                p["numero_ticket"],
                _fecha_hora(p["fecha_entrada"]),
                p["vehiculo"]["placa"] if p["vehiculo"] else "—",
                (p["conductor"]["nombre"][:15] if p["conductor"] else "—"),
                (p["producto"]["nombre"][:15] if p["producto"] else "—"),
                f"{float(p['peso_bruto'] or 0):,.0f}",
                f"{float(p['peso_tara'] or 0):,.0f}",
                f"{neto:,.0f}",
                p["estado"].upper()
            ), tags=(tag,))

        self._tree.tag_configure("par",  background=UI["color_card"])
        self._tree.tag_configure("impar", background=UI["color_bg"])

        self._lbl_count.configure(text=f"{len(self._pesadas)} registros")
        self._lbl_total.configure(text=f"Total Neto: {total_neto:,.2f} KG")

    def _guardar_y_abrir(self, contenido: bytes, nombre: str) -> str:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        ruta = os.path.join(REPORTS_DIR, nombre)
        with open(ruta, "wb") as f:
            f.write(contenido)
        return ruta

    def _ver_ticket(self):
        """Descarga y abre el ticket de la pesada seleccionada en la
        tabla (no todo el kardex) -- antes solo se podía exportar la
        lista completa en PDF/Excel, no bajar el ticket de un camión
        específico."""
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("Ver Ticket", "Seleccione una pesada de la tabla primero.")
            return

        pesada_id = int(sel[0])
        pesada = next((p for p in self._pesadas if p["id"] == pesada_id), None)
        if not pesada:
            return

        try:
            contenido = api_client.descargar_ticket_pdf(pesada_id)
            ruta = self._guardar_y_abrir(contenido, f"TICKET_{pesada['numero_ticket']}.pdf")
            if messagebox.askyesno(
                "Ticket generado",
                f"Ticket {pesada['numero_ticket']}\n"
                f"Placa: {pesada['vehiculo']['placa'] if pesada['vehiculo'] else '—'}\n"
                f"Neto: {float(pesada['peso_neto'] or 0):,.0f} KG\n\n"
                "¿Abrir el archivo?"
            ):
                os.startfile(ruta)
        except (ApiError, OSError) as e:
            messagebox.showerror("Error", f"Error al generar el ticket: {e}")

    def _exportar_pdf(self):
        if not self._pesadas:
            messagebox.showwarning("Sin datos", "No hay datos para exportar")
            return
        try:
            contenido = api_client.descargar_kardex_pdf(**self._filtros_actuales)
            ruta = self._guardar_y_abrir(contenido, f"KARDEX_{datetime.now():%Y%m%d_%H%M%S}.pdf")
            if messagebox.askyesno("PDF Generado",
                    f"PDF generado exitosamente.\n\n¿Abrir el archivo?"):
                os.startfile(ruta)
        except (ApiError, OSError) as e:
            messagebox.showerror("Error", f"Error al generar PDF: {e}")

    def _exportar_excel(self):
        if not self._pesadas:
            messagebox.showwarning("Sin datos", "No hay datos para exportar")
            return
        try:
            contenido = api_client.descargar_kardex_excel(**self._filtros_actuales)
            ruta = self._guardar_y_abrir(contenido, f"KARDEX_{datetime.now():%Y%m%d_%H%M%S}.xlsx")
            if messagebox.askyesno("Excel Generado",
                    f"Excel generado exitosamente.\n\n¿Abrir el archivo?"):
                os.startfile(ruta)
        except (ApiError, OSError) as e:
            messagebox.showerror("Error", f"Error al generar Excel: {e}")
