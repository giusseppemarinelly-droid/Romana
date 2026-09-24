# ============================================================
# gui/centro_costos/centro_costos_view.py
# ============================================================
# Vista EXCLUSIVA para el departamento de Centro de Costos.
# Muestra la cola de pesadas pendientes de aprobación y
# permite APROBAR o RECHAZAR cada una.

import customtkinter as ctk
from tkinter import messagebox, ttk
from datetime import datetime
from config import UI
from client.api_client import api_client, ApiError
from client.ws_client import WsClient
from gui.async_utils import cargar_en_hilo
from gui.components.ui_kit import (
    Card, titulo_h2, boton_primario, boton_secundario, boton_peligro, ocultar_scrollbar,
    etiqueta_campo, texto_ayuda,
)

# Mismo mínimo que exige rechazar_pesada() en services/pesaje_service.py:
# con menos, el backend responde 400 igual -- mejor avisarlo antes.
MOTIVO_RECHAZO_MINIMO = 3


def _fecha_hora(iso_str):
    if not iso_str:
        return "—"
    return datetime.fromisoformat(iso_str).strftime("%d/%m/%Y %H:%M")


class CentroCostosView(ctk.CTkFrame):
    """
    Panel de aprobación para Centro de Costos.

    FLUJO:
      Romana captura 2° peso → estado 'pendiente_aprobacion'
      CC ve la pesada aquí → aprueba o rechaza
      Si aprueba → estado 'aprobado' (Romana completa datos)
      Si rechaza → estado 'rechazado' (Romana vuelve a capturar)
    """

    def __init__(self, parent, callback_navegar=None):
        super().__init__(parent, fg_color="transparent")
        self.callback_navegar = callback_navegar
        self._pesada_seleccionada = None
        self._construir()
        self._cargar_cola()

        # Refresco automático en tiempo real: reemplaza al botón manual
        # "↻ Actualizar" como única forma de enterarse de pesadas nuevas.
        self._ws = WsClient(
            token=api_client.token,
            widget=self,
            on_evento=self._on_evento_ws,
            on_reconectar=self._cargar_cola,  # resincroniza tras una caída de red
        )
        self._ws.iniciar()
        self.bind("<Destroy>", self._on_destroy)

    def _on_destroy(self, event):
        if event.widget is self:
            self._ws.detener()

    def _on_evento_ws(self, evento: dict):
        if evento.get("tipo") == "pesada_pendiente_aprobacion":
            self._cargar_cola()

    # ----------------------------------------------------------
    def _construir(self):
        # minsize para que el panel derecho no quede apachurrado contra el
        # borde en monitores de menor resolución (mismo fix que
        # pesaje_entrada_view.py / pesaje_salida_view.py). Las
        # auto-aprobadas (solo lectura) se separaron a su propia
        # pantalla (gui/centro_costos/auto_aprobadas_view.py) -- esta
        # pantalla ahora es solo cola + detalle, a pantalla completa.
        self.grid_columnconfigure(0, weight=3, minsize=420)
        self.grid_columnconfigure(1, weight=2, minsize=260)
        self.grid_rowconfigure(0, weight=1)

        self._construir_lista()
        self._construir_panel_detalle()

    # ----------------------------------------------------------
    def _construir_lista(self):
        """Panel izquierdo — cola de aprobaciones."""
        frame = Card(self)
        frame.grid(row=0, column=0, sticky="nsew",
                   padx=(20, 8), pady=20)
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # Header
        header_row = ctk.CTkFrame(frame, fg_color="transparent")
        header_row.grid(row=0, column=0, columnspan=2, sticky="ew",
                         padx=16, pady=(16, 4))
        header_row.grid_columnconfigure(0, weight=1)

        titulo_h2(header_row, "📋  Cola de Aprobaciones — Centro de Costos").grid(
            row=0, column=0, sticky="w")

        self._lbl_count = ctk.CTkLabel(
            header_row, text="0 pendientes",
            font=ctk.CTkFont(family=UI["fuente"], size=11),
            text_color=UI["color_muted"]
        )
        self._lbl_count.grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(
            frame,
            text="Seleccione una pesada para ver el detalle y tomar una decisión.",
            font=ctk.CTkFont(family=UI["fuente"], size=11),
            text_color=UI["color_muted"],
            justify="left"
        ).grid(row=1, column=0, padx=16, pady=(0, 8), sticky="w")

        # Tabla
        style = ttk.Style()
        style.theme_use("default")
        style.configure("CC.Treeview",
            background=UI["color_card"],
            foreground=UI["color_text"],
            fieldbackground=UI["color_input_bg"],
            rowheight=34,
            font=("Segoe UI", 11)
        )
        style.configure("CC.Treeview.Heading",
            background=UI["color_bg"],
            foreground=UI["color_warning"],
            font=("Segoe UI", 10, "bold")
        )
        style.map("CC.Treeview",
            background=[("selected", UI["color_accent_tint"])],
            foreground=[("selected", UI["color_warning"])]
        )

        cols = ("ticket", "placa", "tipo", "producto",
                "peso_entrada", "peso_salida", "neto", "empresa")
        self._tree = ttk.Treeview(frame, columns=cols, show="headings",
                                   style="CC.Treeview", selectmode="browse")

        configs = [
            ("ticket",      "TICKET",       100),
            ("placa",       "PLACA",         80),
            ("tipo",        "TIPO",          90),
            ("producto",    "PRODUCTO",     130),
            ("peso_entrada","PESO ENT.",      90),
            ("peso_salida", "PESO SAL.",      90),
            ("neto",        "NETO KG",        90),
            ("empresa",     "EMPRESA",       140),
        ]
        for col, titulo, ancho in configs:
            self._tree.heading(col, text=titulo)
            self._tree.column(col, width=ancho, minwidth=60)

        scroll = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll.set)
        self._tree.grid(row=2, column=0, sticky="nsew", padx=(10, 0))
        scroll.grid(row=2, column=1, sticky="ns")
        self._tree.bind("<<TreeviewSelect>>", self._on_seleccion)

        boton_secundario(
            frame, "↻  Actualizar", command=self._cargar_cola,
            height=30, width=120,
        ).grid(row=3, column=0, padx=10, pady=(6, 12), sticky="w")

    # ----------------------------------------------------------
    def _construir_panel_detalle(self):
        """Panel derecho — detalle + botones de decisión."""
        self._panel = Card(self)
        self._panel.grid(row=0, column=1, sticky="nsew",
                          padx=(8, 20), pady=20)
        self._panel.grid_columnconfigure(0, weight=1)
        self._panel.grid_rowconfigure(0, weight=1)

        self._lbl_placeholder = ctk.CTkLabel(
            self._panel,
            text="← Seleccione una pesada\npara revisar y decidir",
            font=ctk.CTkFont(family=UI["fuente"], size=14),
            text_color=UI["color_muted"],
            justify="center"
        )
        self._lbl_placeholder.grid(row=0, column=0, padx=20, pady=60)

        # Scrollable -- el detalle (datos de guía incluidos) puede superar
        # la altura disponible en monitores más chicos; sin esto, los
        # botones APROBAR/RECHAZAR quedaban directamente inalcanzables,
        # cortados por el borde de la ventana sin ningún aviso (mismo
        # síntoma que el fix de pesaje_entrada_view.py, ver CLAUDE.md).
        self._detalle_frame = ctk.CTkScrollableFrame(self._panel, fg_color="transparent")
        ocultar_scrollbar(self._detalle_frame)

    # ----------------------------------------------------------
    def _cargar_cola(self):
        for item in self._tree.get_children():
            self._tree.delete(item)

        cargar_en_hilo(
            self, api_client.listar_pendientes_aprobacion,
            on_exito=self._poblar_cola,
            on_error=lambda e: messagebox.showerror("Error de conexión", str(e)),
        )

    def _poblar_cola(self, pesadas):
        for p in pesadas:
            tipo = "General" if p["tipo_pesaje"] == "GENERAL" else "Prod. Term."
            empresa = (p["empresa_cliente_proveedor"] or
                       p["empresa_transportista"] or "—")
            self._tree.insert("", "end", iid=str(p["id"]), values=(
                p["numero_ticket"],
                p["vehiculo"]["placa"] if p["vehiculo"] else "—",
                tipo,
                (p["producto"]["nombre"][:14] if p["producto"] else "—"),
                f"{float(p['peso_bruto'] or 0):,.0f}",
                f"{float(p['peso_tara'] or 0):,.0f}",
                f"{float(p['peso_neto'] or 0):,.0f}",
                empresa[:18]
            ))

        self._lbl_count.configure(
            text=f"{len(pesadas)} pendiente(s)",
            text_color=UI["color_warning"] if pesadas else UI["color_muted"]
        )
        self._pesada_seleccionada = None
        self._limpiar_detalle()

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
            self._mostrar_detalle(p)

    # ----------------------------------------------------------
    def _mostrar_detalle(self, p):
        """Muestra el detalle completo de la pesada seleccionada."""
        self._lbl_placeholder.grid_forget()
        self._detalle_frame.grid(row=0, column=0, sticky="nsew",
                                  padx=16, pady=16)
        self._detalle_frame.grid_columnconfigure(0, weight=1)

        for w in self._detalle_frame.winfo_children():
            w.destroy()

        row = 0

        # Título
        ctk.CTkLabel(
            self._detalle_frame,
            text=f"Ticket  {p['numero_ticket']}",
            font=ctk.CTkFont(family=UI["fuente"], size=16, weight="bold"),
            text_color=UI["color_warning"]
        ).grid(row=row, column=0, sticky="w", pady=(0, 4)); row += 1

        ctk.CTkLabel(
            self._detalle_frame,
            text=f"Vehículo: {p['vehiculo']['placa'] if p['vehiculo'] else '—'}",
            font=ctk.CTkFont(family=UI["fuente"], size=12),
            text_color=UI["color_muted"]
        ).grid(row=row, column=0, sticky="w"); row += 1

        # Separador
        ctk.CTkFrame(self._detalle_frame, height=1,
                      fg_color=UI["color_border"]).grid(
            row=row, column=0, sticky="ew", pady=10); row += 1

        # Datos del pesaje
        peso_guia = float(p["peso_guia"] or 0)
        neto = float(p["peso_neto"] or 0)
        diferencia_txt = (f"{abs(neto - peso_guia) / peso_guia * 100:,.2f} %"
                           if peso_guia else "—")

        infos = [
            ("Tipo de pesaje",
             "Pesaje General" if p["tipo_pesaje"] == "GENERAL" else "Producto Terminado"),
            ("Producto", p["producto"]["nombre"] if p["producto"] else "—"),
            ("Empresa transportista", p["empresa_transportista"] or "—"),
            ("Empresa cliente/proveedor", p["empresa_cliente_proveedor"] or "—"),
            ("Cédula conductor", p["cedula_conductor_libre"] or "—"),
            ("Fecha pre-pesaje", _fecha_hora(p["fecha_captura"])),
            ("Código de viaje", p["codigo_viaje"] or "—"),
            ("Peso guía", f"{peso_guia:,.0f} KG" if p["peso_guia"] is not None else "—"),
            ("Bultos", p["bultos"] if p["bultos"] is not None else "—"),
            ("Diferencia c/ guía", diferencia_txt),
        ]
        for etiq, val in infos:
            self._fila(self._detalle_frame, row, etiq, val); row += 1

        # Separador
        ctk.CTkFrame(self._detalle_frame, height=1,
                      fg_color=UI["color_border"]).grid(
            row=row, column=0, sticky="ew", pady=10); row += 1

        # Pesos en grande
        pesos_frame = ctk.CTkFrame(self._detalle_frame,
                                    fg_color=UI["color_bg"],
                                    corner_radius=10)
        pesos_frame.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        pesos_frame.grid_columnconfigure((0, 1, 2), weight=1)
        row += 1

        self._peso_grande(pesos_frame, 0, "ENTRADA",
            f"{float(p['peso_bruto'] or 0):,.0f} KG", UI["color_muted"])
        self._peso_grande(pesos_frame, 1, "SALIDA",
            f"{float(p['peso_tara'] or 0):,.0f} KG", UI["color_warning"])
        self._peso_grande(pesos_frame, 2, "NETO",
            f"{float(p['peso_neto'] or 0):,.0f} KG", UI["color_success"])

        # Separador
        ctk.CTkFrame(self._detalle_frame, height=1,
                      fg_color=UI["color_border"]).grid(
            row=row, column=0, sticky="ew", pady=10); row += 1

        # Comentario de la decisión: un solo campo para las dos acciones,
        # escrito justo antes de apretar. Al aprobar es opcional (por qué se
        # acepta, ej. una diferencia con la guía que está justificada); al
        # rechazar es el motivo, obligatorio -- Romana lo ve al re-pesar.
        etiqueta_campo(self._detalle_frame, "Comentario de la decisión").grid(
            row=row, column=0, sticky="w"); row += 1
        texto_ayuda(
            self._detalle_frame, "Opcional al aprobar · obligatorio al rechazar",
        ).grid(row=row, column=0, sticky="w", pady=(0, 4)); row += 1

        self._txt_comentario = ctk.CTkTextbox(
            self._detalle_frame, height=72, wrap="word",
            font=ctk.CTkFont(family=UI["fuente"], size=UI["fuente_body"]),
            fg_color=UI["color_input_bg"], text_color=UI["color_text"],
            border_color=UI["color_border"], border_width=1,
            corner_radius=UI["radio_control"],
        )
        self._txt_comentario.grid(row=row, column=0, sticky="ew", pady=(0, 12)); row += 1

        # Botón APROBAR
        boton_primario(
            self._detalle_frame, "✅  APROBAR", command=self._aprobar, height=50,
        ).grid(row=row, column=0, sticky="ew", pady=(0, 6)); row += 1

        # Botón RECHAZAR
        boton_peligro(
            self._detalle_frame, "❌  RECHAZAR", command=self._rechazar, height=40,
        ).grid(row=row, column=0, sticky="ew"); row += 1

    # ----------------------------------------------------------
    def _fila(self, parent, row, etiqueta, valor):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, sticky="ew", pady=2)
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            frame, text=f"{etiqueta}:",
            font=ctk.CTkFont(family=UI["fuente"], size=10),
            text_color=UI["color_muted"], width=150, anchor="w"
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            frame, text=str(valor),
            font=ctk.CTkFont(family=UI["fuente"], size=11, weight="bold"),
            text_color=UI["color_text"], anchor="w", wraplength=180
        ).grid(row=0, column=1, sticky="w")

    # ----------------------------------------------------------
    def _peso_grande(self, parent, col, label, valor, color):
        ctk.CTkLabel(
            parent, text=label,
            font=ctk.CTkFont(family=UI["fuente"], size=9, weight="bold"),
            text_color=UI["color_muted"]
        ).grid(row=0, column=col, padx=8, pady=(10, 2))

        ctk.CTkLabel(
            parent, text=valor,
            font=ctk.CTkFont(family=UI["fuente"], size=16, weight="bold"),
            text_color=color
        ).grid(row=1, column=col, padx=8, pady=(0, 10))

    # ----------------------------------------------------------
    def _comentario(self) -> str:
        return self._txt_comentario.get("1.0", "end").strip()

    # ----------------------------------------------------------
    def _aprobar(self):
        if not self._pesada_seleccionada:
            return

        comentario = self._comentario()
        if not messagebox.askyesno(
            "Confirmar aprobación",
            f"¿Aprobar la pesada {self._pesada_seleccionada['numero_ticket']}?\n\n"
            f"Neto: {float(self._pesada_seleccionada['peso_neto'] or 0):,.0f} KG\n"
            f"Comentario: {comentario or '(sin comentario)'}\n\n"
            "Al aprobar, la Romana podrá completar los datos finales."
        ):
            return

        resultado = api_client.aprobar_pesada(self._pesada_seleccionada["id"], comentario)

        if resultado["exito"]:
            messagebox.showinfo(
                "Aprobada ✓",
                f"Pesada {self._pesada_seleccionada['numero_ticket']} aprobada.\n"
                "La Romana recibirá la notificación para completar los datos."
            )
            self._cargar_cola()
        else:
            messagebox.showerror("Error", resultado["mensaje"])

    # ----------------------------------------------------------
    def _rechazar(self):
        if not self._pesada_seleccionada:
            return

        motivo = self._comentario()
        if len(motivo) < MOTIVO_RECHAZO_MINIMO:
            messagebox.showwarning(
                "Falta el motivo",
                "Para rechazar, escriba el motivo en \"Comentario de la decisión\".\n"
                "La Romana lo va a ver al volver a pesar el camión.",
            )
            self._txt_comentario.focus_set()
            return

        if not messagebox.askyesno(
            "Confirmar rechazo",
            f"¿Rechazar la pesada {self._pesada_seleccionada['numero_ticket']}?\n\n"
            f"Motivo: {motivo}\n\n"
            "La Romana deberá volver a capturar el peso."
        ):
            return

        resultado = api_client.rechazar_pesada(self._pesada_seleccionada["id"], motivo)

        if resultado["exito"]:
            messagebox.showinfo(
                "Rechazada",
                f"Pesada rechazada.\n"
                f"Motivo: {motivo}\n\n"
                "La Romana deberá volver a capturar el peso."
            )
            self._cargar_cola()
        else:
            messagebox.showerror("Error", resultado["mensaje"])

    # ----------------------------------------------------------
    def _limpiar_detalle(self):
        for w in self._detalle_frame.winfo_children():
            w.destroy()
        self._detalle_frame.grid_forget()
        self._lbl_placeholder.grid(row=0, column=0, padx=20, pady=60)
