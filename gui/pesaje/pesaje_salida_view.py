# ============================================================
# gui/pesaje/pesaje_salida_view.py — Captura de Peso (Salida)
# ============================================================

import customtkinter as ctk
from tkinter import messagebox, ttk
from datetime import datetime
from config import UI
from client.api_client import api_client, ApiError
from hardware.display_manager import leer_peso_actual, es_peso_estable
from gui.async_utils import cargar_en_hilo


def _hora(iso_str):
    """La API devuelve fechas como texto ISO 8601 — se parsean para mostrar solo HH:MM."""
    if not iso_str:
        return "—"
    return datetime.fromisoformat(iso_str).strftime("%H:%M")


class PesajeSalidaView(ctk.CTkFrame):
    """
    Pantalla de salida / captura del 2° peso.

    FLUJO:
      1. Muestra cola de camiones EN PLANTA (estado='en_planta' o 'rechazado')
      2. Operador selecciona un camión
      3. Aparece panel derecho con info + peso actual de la báscula
      4. Botón [CAPTURAR PESO] → estado='pendiente_aprobacion' → va a CC
    """

    def __init__(self, parent, callback_navegar=None):
        super().__init__(parent, fg_color="transparent")
        self.callback_navegar = callback_navegar
        self._pesada_seleccionada = None
        self._after_id_peso_live = None
        self._construir()
        self._cargar_cola()

    def destroy(self):
        # _actualizar_peso_live() se reprograma solo con self.after()
        # cada 2s mientras hay un camión seleccionado -- sin cancelarlo
        # acá, al navegar a otra pantalla el timer sigue vivo leyendo la
        # báscula cada 2s contra widgets ya destruidos (ver mismo fix en
        # pesaje_entrada_view.py).
        if self._after_id_peso_live is not None:
            self.after_cancel(self._after_id_peso_live)
            self._after_id_peso_live = None
        super().destroy()

    # ----------------------------------------------------------
    def _construir(self):
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        self._construir_lista()
        self._construir_panel_detalle()

    # ----------------------------------------------------------
    def _construir_lista(self):
        """Panel izquierdo — cola de camiones en planta."""
        frame = ctk.CTkFrame(self, fg_color=UI["color_card"],
                              border_color=UI["color_border"],
                              border_width=1, corner_radius=12)
        frame.grid(row=0, column=0, sticky="nsew",
                   padx=(20, 8), pady=20)
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # Header
        ctk.CTkLabel(
            frame, text="↑  CAMIONES EN PLANTA",
            font=ctk.CTkFont(family=UI["fuente"], size=14, weight="bold"),
            text_color=UI["color_accent"]
        ).grid(row=0, column=0, padx=16, pady=(16, 4), sticky="w")

        ctk.CTkLabel(
            frame,
            text="Seleccione el camión que ya está cargado para capturar su peso de salida.",
            font=ctk.CTkFont(family=UI["fuente"], size=11),
            text_color=UI["color_muted"],
            wraplength=400, justify="left"
        ).grid(row=1, column=0, padx=16, pady=(0, 8), sticky="w")

        # Tabla
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Salida.Treeview",
            background="#ffffff",
            foreground="#1e293b",
            fieldbackground="#f8fafc",
            rowheight=32,
            font=("Segoe UI", 11)
        )
        style.configure("Salida.Treeview.Heading",
            background="#f1f5f9",
            foreground="#1e293b",
            font=("Segoe UI", 10, "bold")
        )
        style.map("Salida.Treeview",
            background=[("selected", "#dbeafe")],
            foreground=[("selected", "#1e3a8a")]
        )

        cols = ("ticket", "placa", "tipo", "producto", "peso_entrada", "estado", "hora")
        self._tree = ttk.Treeview(frame, columns=cols, show="headings",
                                   style="Salida.Treeview", selectmode="browse")

        configs = [
            ("ticket",       "TICKET",      100),
            ("placa",        "PLACA",        85),
            ("tipo",         "TIPO",         90),
            ("producto",     "PRODUCTO",    140),
            ("peso_entrada", "PESO ENTR.",   95),
            ("estado",       "ESTADO",       90),
            ("hora",         "HORA ENTR.",   80),
        ]
        for col, titulo, ancho in configs:
            self._tree.heading(col, text=titulo)
            self._tree.column(col, width=ancho, minwidth=60)

        scroll = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll.set)

        self._tree.grid(row=2, column=0, sticky="nsew", padx=(10, 0), pady=(0, 8))
        scroll.grid(row=2, column=1, sticky="ns")

        self._tree.bind("<<TreeviewSelect>>", self._on_seleccion)

        # Botones de acción
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.grid(row=3, column=0, columnspan=2, sticky="ew",
                       padx=10, pady=(0, 12))

        ctk.CTkButton(
            btn_frame, text="↻  Actualizar lista",
            command=self._cargar_cola,
            height=32, width=150,
            fg_color="transparent",
            border_color=UI["color_border"], border_width=1,
            text_color=UI["color_text"],
            hover_color=UI["color_bg"],
            font=ctk.CTkFont(family=UI["fuente"], size=12)
        ).pack(side="left", padx=(0, 8))

        # Contador
        self._lbl_count = ctk.CTkLabel(
            btn_frame, text="0 camiones",
            font=ctk.CTkFont(family=UI["fuente"], size=11),
            text_color=UI["color_muted"]
        )
        self._lbl_count.pack(side="right")

    # ----------------------------------------------------------
    def _construir_panel_detalle(self):
        """Panel derecho — detalle del camión seleccionado + captura."""
        self._panel_detalle = ctk.CTkFrame(
            self, fg_color=UI["color_card"],
            border_color=UI["color_border"],
            border_width=1, corner_radius=12
        )
        self._panel_detalle.grid(row=0, column=1, sticky="nsew",
                                  padx=(8, 20), pady=20)
        self._panel_detalle.grid_columnconfigure(0, weight=1)

        # Estado inicial: sin selección
        self._lbl_sin_sel = ctk.CTkLabel(
            self._panel_detalle,
            text="← Seleccione un camión\nde la lista",
            font=ctk.CTkFont(family=UI["fuente"], size=14),
            text_color=UI["color_muted"],
            justify="center"
        )
        self._lbl_sin_sel.grid(row=0, column=0, padx=20, pady=80)

        # Contenedor del detalle (se muestra al seleccionar)
        self._detalle_frame = ctk.CTkFrame(
            self._panel_detalle, fg_color="transparent")

    # ----------------------------------------------------------
    def _cargar_cola(self):
        """Carga los camiones en planta (incluyendo rechazados)."""
        for item in self._tree.get_children():
            self._tree.delete(item)

        def _fetch():
            pesadas = api_client.listar_pesadas_en_planta()
            # También mostrar rechazados (CC rechazó, Romana debe recapturar)
            rechazadas = api_client.get_kardex(estado="rechazado")
            return pesadas + rechazadas

        cargar_en_hilo(
            self, _fetch,
            on_exito=self._on_cola_cargada,
            on_error=lambda e: messagebox.showerror("Error de conexión", str(e)),
        )

    def _on_cola_cargada(self, todos):
        for p in todos:
            prod_nombre = p["producto"]["nombre"][:14] if p["producto"] else "—"
            tipo = "General" if p["tipo_pesaje"] == "GENERAL" else "Prod. Term."
            estado_texto = "🔴 Rechazado" if p["estado"] == "rechazado" else "🟡 En planta"

            self._tree.insert("", "end", iid=str(p["id"]), values=(
                p["numero_ticket"],
                p["vehiculo"]["placa"] if p["vehiculo"] else "—",
                tipo,
                prod_nombre,
                f"{float(p['peso_bruto'] or 0):,.0f} kg",
                estado_texto,
                _hora(p["fecha_entrada"])
            ))

        self._lbl_count.configure(text=f"{len(todos)} camión(es)")
        self._pesada_seleccionada = None
        self._limpiar_detalle()

    # ----------------------------------------------------------
    def _on_seleccion(self, event):
        sel = self._tree.selection()
        if not sel:
            return

        pesada_id = int(sel[0])
        try:
            pesada = api_client.obtener_pesada(pesada_id)
        except ApiError as e:
            messagebox.showerror("Error de conexión", str(e))
            return

        if pesada:
            self._pesada_seleccionada = pesada
            self._mostrar_detalle(pesada)

    # ----------------------------------------------------------
    def _mostrar_detalle(self, p):
        """Muestra el panel de captura para el camión seleccionado."""
        # Si ya había un timer de peso en vivo de una selección anterior,
        # cancelarlo -- si no, cada camión seleccionado en la sesión deja
        # su propio timer corriendo de fondo además del nuevo.
        if self._after_id_peso_live is not None:
            self.after_cancel(self._after_id_peso_live)
            self._after_id_peso_live = None

        self._lbl_sin_sel.grid_forget()
        self._detalle_frame.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        self._detalle_frame.grid_columnconfigure(0, weight=1)

        # Limpiar widgets anteriores
        for w in self._detalle_frame.winfo_children():
            w.destroy()

        row = 0

        # Título
        ctk.CTkLabel(
            self._detalle_frame,
            text=f"🚛  {p['vehiculo']['placa'] if p['vehiculo'] else '—'}",
            font=ctk.CTkFont(family=UI["fuente"], size=18, weight="bold"),
            text_color=UI["color_text"]
        ).grid(row=row, column=0, sticky="w", pady=(0, 4)); row += 1

        ctk.CTkLabel(
            self._detalle_frame,
            text=f"Ticket: {p['numero_ticket']}",
            font=ctk.CTkFont(family=UI["fuente"], size=12),
            text_color=UI["color_muted"]
        ).grid(row=row, column=0, sticky="w", pady=(0, 10)); row += 1

        # Separador
        ctk.CTkFrame(self._detalle_frame, height=1,
                      fg_color=UI["color_border"]).grid(
            row=row, column=0, sticky="ew", pady=6); row += 1

        # Info de entrada
        self._fila_info(self._detalle_frame, row, "Tipo:",
            "Pesaje General" if p["tipo_pesaje"] == "GENERAL" else "Producto Terminado")
        row += 1
        self._fila_info(self._detalle_frame, row, "Producto:",
            p["producto"]["nombre"] if p["producto"] else "—"); row += 1
        self._fila_info(self._detalle_frame, row, "Empresa transp.:",
            p["empresa_transportista"] or "—"); row += 1
        self._fila_info(self._detalle_frame, row, "Empresa cliente:",
            p["empresa_cliente_proveedor"] or "—"); row += 1
        self._fila_info(self._detalle_frame, row, "Peso entrada:",
            f"{float(p['peso_bruto'] or 0):,.0f} KG",
            color=UI["color_accent"]); row += 1

        # Rechazo previo (si aplica)
        if p["estado"] == "rechazado" and p["motivo_rechazo"]:
            ctk.CTkFrame(self._detalle_frame, height=1,
                          fg_color="#fecaca").grid(
                row=row, column=0, sticky="ew", pady=6); row += 1

            ctk.CTkLabel(
                self._detalle_frame,
                text=f"❌ RECHAZADO por CC:\n{p['motivo_rechazo']}",
                font=ctk.CTkFont(family=UI["fuente"], size=11),
                text_color="#dc2626",
                wraplength=280, justify="left"
            ).grid(row=row, column=0, sticky="w", pady=(0, 8)); row += 1

        # Separador
        ctk.CTkFrame(self._detalle_frame, height=1,
                      fg_color=UI["color_border"]).grid(
            row=row, column=0, sticky="ew", pady=6); row += 1

        # Peso actual de la báscula
        ctk.CTkLabel(
            self._detalle_frame, text="PESO ACTUAL BÁSCULA",
            font=ctk.CTkFont(family=UI["fuente"], size=10, weight="bold"),
            text_color=UI["color_muted"]
        ).grid(row=row, column=0, sticky="w"); row += 1

        self._lbl_peso_actual = ctk.CTkLabel(
            self._detalle_frame, text="--- KG",
            font=ctk.CTkFont(family=UI["fuente"], size=30, weight="bold"),
            text_color=UI["color_success"]
        )
        self._lbl_peso_actual.grid(row=row, column=0, pady=4); row += 1

        self._lbl_neto_preview = ctk.CTkLabel(
            self._detalle_frame, text="NETO estimado: — KG",
            font=ctk.CTkFont(family=UI["fuente"], size=13),
            text_color=UI["color_muted"]
        )
        self._lbl_neto_preview.grid(row=row, column=0, pady=(0, 8)); row += 1

        # Botón capturar
        self._btn_capturar = ctk.CTkButton(
            self._detalle_frame,
            text="⚖  CAPTURAR PESO\n→ Enviar a Centro de Costos",
            command=self._capturar_peso,
            height=60,
            font=ctk.CTkFont(family=UI["fuente"], size=13, weight="bold"),
            fg_color=UI["color_success"],
            hover_color="#059669",
            corner_radius=10
        )
        self._btn_capturar.grid(row=row, column=0, sticky="ew", pady=(4, 8)); row += 1

        # Botón anular
        ctk.CTkButton(
            self._detalle_frame,
            text="🗑  Anular esta entrada",
            command=self._anular,
            height=32,
            fg_color="transparent",
            border_color="#fca5a5", border_width=1,
            text_color="#dc2626",
            hover_color="#fef2f2",
            font=ctk.CTkFont(family=UI["fuente"], size=11)
        ).grid(row=row, column=0, sticky="ew"); row += 1

        # Iniciar actualización en vivo
        self._actualizar_peso_live()

    # ----------------------------------------------------------
    def _fila_info(self, parent, row, etiqueta, valor, color=None):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, sticky="ew", pady=2)
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            frame, text=etiqueta,
            font=ctk.CTkFont(family=UI["fuente"], size=11),
            text_color=UI["color_muted"], width=120, anchor="w"
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            frame, text=str(valor),
            font=ctk.CTkFont(family=UI["fuente"], size=11, weight="bold"),
            text_color=color or UI["color_text"], anchor="w"
        ).grid(row=0, column=1, sticky="w")

    # ----------------------------------------------------------
    def _actualizar_peso_live(self):
        """Actualiza el peso en vivo mientras hay un camión seleccionado."""
        if not self._pesada_seleccionada:
            return
        if not hasattr(self, "_lbl_peso_actual"):
            return

        try:
            peso = leer_peso_actual() or 0.0
            self._lbl_peso_actual.configure(text=f"{peso:,.0f} KG")

            # Calcular neto estimado
            if self._pesada_seleccionada and peso > 0:
                p1 = float(self._pesada_seleccionada["peso_bruto"] or 0)
                p2 = float(peso)
                neto = abs(p2 - p1)
                self._lbl_neto_preview.configure(
                    text=f"NETO estimado: {neto:,.0f} KG",
                    text_color=UI["color_accent"]
                )
        except Exception:
            pass

        self._after_id_peso_live = self.after(2000, self._actualizar_peso_live)

    # ----------------------------------------------------------
    def _capturar_peso(self):
        if not self._pesada_seleccionada:
            return

        try:
            peso = leer_peso_actual() or 0.0
        except Exception:
            peso = 0.0

        if peso <= 0:
            messagebox.showerror(
                "Sin peso",
                "No hay un peso válido en la báscula.\n"
                "Asegúrese de que el camión esté sobre la báscula."
            )
            return

        p1 = float(self._pesada_seleccionada["peso_bruto"] or 0)
        neto = abs(float(peso) - p1)

        if not messagebox.askyesno(
            "Confirmar captura",
            f"Camión: {self._pesada_seleccionada['vehiculo']['placa']}\n"
            f"Peso entrada: {p1:,.0f} KG\n"
            f"Peso actual:  {peso:,.0f} KG\n"
            f"NETO:         {neto:,.0f} KG\n\n"
            "¿Capturar y enviar a Centro de Costos para aprobación?"
        ):
            return

        resultado = api_client.capturar_salida(
            pesada_id=self._pesada_seleccionada["id"],
            peso_capturado=float(peso)
        )

        if resultado["exito"]:
            messagebox.showinfo(
                "Enviado a Centro de Costos ✓",
                f"Ticket: {self._pesada_seleccionada['numero_ticket']}\n"
                f"Peso neto: {resultado['peso_neto']:,.0f} KG\n\n"
                "La pesada fue enviada a Centro de Costos.\n"
                "Espere la aprobación para completar los datos finales."
            )
            self._cargar_cola()
        else:
            messagebox.showerror("Error", resultado["mensaje"])

    # ----------------------------------------------------------
    def _anular(self):
        if not self._pesada_seleccionada:
            return

        motivo = ctk.CTkInputDialog(
            text=f"Ingrese el motivo de anulación para el ticket {self._pesada_seleccionada['numero_ticket']}:",
            title="Anular entrada"
        ).get_input()

        if not motivo:
            return

        resultado = api_client.anular_pesada(self._pesada_seleccionada["id"], motivo)
        if resultado["exito"]:
            messagebox.showinfo("Anulada", resultado["mensaje"])
            self._cargar_cola()
        else:
            messagebox.showerror("Error", resultado["mensaje"])

    # ----------------------------------------------------------
    def _limpiar_detalle(self):
        for w in self._detalle_frame.winfo_children():
            w.destroy()
        self._detalle_frame.grid_forget()
        self._lbl_sin_sel.grid(row=0, column=0, padx=20, pady=80)
