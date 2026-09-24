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
from hardware.display_manager import leer_peso_actual, es_peso_estable
from gui.async_utils import cargar_en_hilo
from gui.components.ui_kit import (
    Card, boton_primario, boton_secundario, titulo_h2, etiqueta_campo, ocultar_scrollbar,
)
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
        self._peso_final_capturado = None
        self._peso_final_es_manual = False
        self._after_id_peso_final = None
        self._construir()
        self._cargar_lista()

    def destroy(self):
        # _actualizar_peso_final() se reprograma solo con self.after() cada
        # 2s mientras hay una pesada seleccionada -- sin cancelarlo acá, al
        # navegar a otra pantalla el timer sigue vivo leyendo la báscula
        # contra widgets ya destruidos (mismo fix que pesaje_entrada_view.py
        # / pesaje_salida_view.py).
        if self._after_id_peso_final is not None:
            self.after_cancel(self._after_id_peso_final)
            self._after_id_peso_final = None
        super().destroy()

    # ----------------------------------------------------------
    def _construir(self):
        # minsize para que el panel derecho no quede apachurrado contra el
        # borde en monitores de menor resolución (mismo fix que
        # pesaje_entrada_view.py / pesaje_salida_view.py).
        self.grid_columnconfigure(0, weight=3, minsize=420)
        self.grid_columnconfigure(1, weight=2, minsize=260)
        self.grid_rowconfigure(0, weight=1)

        self._construir_lista()
        self._construir_formulario()

    # ----------------------------------------------------------
    def _construir_lista(self):
        frame = Card(self)
        frame.grid(row=0, column=0, sticky="nsew",
                   padx=(20, 8), pady=20)
        frame.grid_rowconfigure(5, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Completar.Treeview",
            background=UI["color_card"],
            foreground=UI["color_text"],
            fieldbackground=UI["color_input_bg"],
            rowheight=32,
            font=("Segoe UI", 11)
        )
        style.configure("Completar.Treeview.Heading",
            background=UI["color_bg"],
            foreground=UI["color_success"],
            font=("Segoe UI", 10, "bold")
        )
        style.map("Completar.Treeview",
            background=[("selected", UI["color_brand_tint"])],
            foreground=[("selected", UI["color_brand"])]
        )
        style.configure("PendCC.Treeview.Heading",
            background=UI["color_bg"],
            foreground=UI["color_warning"],
            font=("Segoe UI", 10, "bold")
        )

        # ── Pendientes de aprobación por CC (solo lectura) ──────
        # Visibilidad de lo que ya se mandó a Centro de Costos y todavía
        # no tiene respuesta -- mientras tanto Facturación puede ir
        # preparando la factura con esos datos. No es seleccionable acá:
        # Romana no puede completar nada hasta que CC decida.
        header_pend = ctk.CTkFrame(frame, fg_color="transparent")
        header_pend.grid(row=0, column=0, columnspan=2, sticky="ew",
                          padx=16, pady=(16, 4))
        header_pend.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header_pend,
            text="⏳  ESPERANDO APROBACIÓN DE CENTRO DE COSTOS",
            font=ctk.CTkFont(family=UI["fuente"], size=12, weight="bold"),
            text_color=UI["color_warning"]
        ).grid(row=0, column=0, sticky="w")

        self._lbl_count_pend_cc = ctk.CTkLabel(
            header_pend, text="0",
            font=ctk.CTkFont(family=UI["fuente"], size=11),
            text_color=UI["color_muted"]
        )
        self._lbl_count_pend_cc.grid(row=0, column=1, sticky="e")

        cols_pend = ("ticket", "placa", "producto", "neto", "hora")
        self._tree_pend_cc = ttk.Treeview(
            frame, columns=cols_pend, show="headings",
            style="PendCC.Treeview", selectmode="none", height=4
        )
        for col, titulo, ancho in [
            ("ticket",   "TICKET",   100),
            ("placa",    "PLACA",     70),
            ("producto", "PRODUCTO", 120),
            ("neto",     "NETO KG",   80),
            ("hora",     "CAPTURA",   70),
        ]:
            self._tree_pend_cc.heading(col, text=titulo)
            self._tree_pend_cc.column(col, width=ancho, minwidth=50)
        self._tree_pend_cc.grid(row=1, column=0, columnspan=2,
                                 sticky="ew", padx=(10, 6))

        ctk.CTkFrame(frame, height=1, fg_color=UI["color_border"]).grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=10)

        # ── Aprobadas por CC, pendientes de completar ───────────
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.grid(row=3, column=0, columnspan=2, sticky="ew",
                     padx=16, pady=(0, 4))
        header.grid_columnconfigure(0, weight=1)

        titulo_h2(header, "✅  Aprobadas por CC — pendientes de completar").grid(
            row=0, column=0, sticky="w")

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
        ).grid(row=4, column=0, padx=16, pady=(0, 8), sticky="w")

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
        self._tree.grid(row=5, column=0, sticky="nsew", padx=(10, 0))
        scroll.grid(row=5, column=1, sticky="ns")
        self._tree.bind("<<TreeviewSelect>>", self._on_seleccion)

        boton_secundario(
            frame, "↻  Actualizar", command=self._cargar_lista,
            height=30, width=120,
        ).grid(row=6, column=0, padx=10, pady=(6, 12), sticky="w")

    # ----------------------------------------------------------
    def _construir_formulario(self):
        """Panel derecho — datos finales a completar."""
        self._panel = Card(self)
        self._panel.grid(row=0, column=1, sticky="nsew",
                          padx=(8, 20), pady=20)
        self._panel.grid_columnconfigure(0, weight=1)
        self._panel.grid_rowconfigure(0, weight=1)

        self._lbl_placeholder = ctk.CTkLabel(
            self._panel,
            text="← Seleccione una pesada\naprobada para completarla",
            font=ctk.CTkFont(family=UI["fuente"], size=14),
            text_color=UI["color_muted"],
            justify="center"
        )
        self._lbl_placeholder.grid(row=0, column=0, padx=20, pady=60)

        # Scrollable -- con Peso Final + los datos finales, el contenido
        # puede superar la altura del panel en monitores más chicos; sin
        # esto, el botón "GUARDAR Y COMPLETAR" quedaba tapado por el
        # borde de la ventana (mismo fix que pesaje_entrada_view.py).
        self._form_frame = ctk.CTkScrollableFrame(
            self._panel, fg_color="transparent", label_text="")
        ocultar_scrollbar(self._form_frame)

    # ----------------------------------------------------------
    def _cargar_lista(self):
        for item in self._tree.get_children():
            self._tree.delete(item)
        for item in self._tree_pend_cc.get_children():
            self._tree_pend_cc.delete(item)

        cargar_en_hilo(
            self, api_client.listar_aprobadas_pendientes,
            on_exito=self._poblar_lista,
            on_error=lambda e: messagebox.showerror("Error de conexión", str(e)),
        )
        cargar_en_hilo(
            self, api_client.listar_pendientes_aprobacion,
            on_exito=self._poblar_lista_pend_cc,
            on_error=lambda e: messagebox.showerror("Error de conexión", str(e)),
        )

    def _poblar_lista_pend_cc(self, pesadas):
        """Solo lectura -- lo que ya está en la cola de Centro de Costos,
        esperando aprobación. Romana no puede completar nada acá todavía."""
        for p in pesadas:
            self._tree_pend_cc.insert("", "end", iid=str(p["id"]), values=(
                p["numero_ticket"],
                p["vehiculo"]["placa"] if p["vehiculo"] else "—",
                (p["producto"]["nombre"][:14] if p["producto"] else "—"),
                f"{float(p['peso_neto'] or 0):,.0f}",
                _hora(p["fecha_captura"])
            ))
        self._lbl_count_pend_cc.configure(text=f"{len(pesadas)}")

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

        self._peso_final_capturado = None
        self._peso_final_es_manual = False
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

        # Por qué aprobó CC (opcional, ver aprobar_pesada) -- útil si hay
        # algo que Romana tenga que saber antes de dejar salir el camión.
        if p.get("comentario_aprobacion"):
            ctk.CTkLabel(
                self._form_frame,
                text=f"Comentario de Costos: {p['comentario_aprobacion']}",
                font=ctk.CTkFont(family=UI["fuente"], size=11),
                text_color=UI["color_text"], wraplength=320, justify="left",
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
            f"{float(p['peso_tara'] or 0):,.0f} KG", UI["color_warning"])
        self._dato_rapido(info_frame, 2, "NETO",
            f"{float(p['peso_neto'] or 0):,.0f} KG", UI["color_success"])

        # Separador
        ctk.CTkFrame(self._form_frame, height=1,
                      fg_color=UI["color_border"]).grid(
            row=row, column=0, sticky="ew", pady=10); row += 1

        # Peso final -- 3er pesaje, el chofer sube a la báscula por
        # última vez antes de autorizar la salida. Se registra sin
        # bloqueo de tolerancia contra el pre-pesaje (solo informativo).
        etiqueta_campo(
            self._form_frame, "⚖  Peso final — antes de autorizar la salida"
        ).grid(row=row, column=0, sticky="w", pady=(0, 4)); row += 1

        self._lbl_peso_final = ctk.CTkLabel(
            self._form_frame, text="--- KG",
            font=ctk.CTkFont(family=UI["fuente"], size=28, weight="bold"),
            text_color=UI["color_accent"]
        )
        self._lbl_peso_final.grid(row=row, column=0, pady=(0, 2)); row += 1

        self._lbl_dif_peso_final = ctk.CTkLabel(
            self._form_frame, text="",
            font=ctk.CTkFont(family=UI["fuente"], size=11),
            text_color=UI["color_muted"]
        )
        self._lbl_dif_peso_final.grid(row=row, column=0, pady=(0, 6)); row += 1

        # Peso manual (si la báscula no responde) -- ver mismo patrón en
        # pesaje_entrada_view.py / pesaje_salida_view.py.
        self._peso_manual_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            self._form_frame, text="⌨  Ingresar peso manualmente",
            variable=self._peso_manual_var, command=self._toggle_peso_manual,
            font=ctk.CTkFont(family=UI["fuente"], size=11),
            fg_color=UI["color_accent"], hover_color=UI["color_accent_hover"],
            border_color=UI["color_border"],
        ).grid(row=row, column=0, pady=(0, 4)); row += 1

        self._entry_peso_manual = ctk.CTkEntry(
            self._form_frame, placeholder_text="Peso en KG",
            height=36, font=ctk.CTkFont(family=UI["fuente"], size=13)
        )
        self._entry_peso_manual.grid(row=row, column=0, sticky="ew", pady=(0, 8)); row += 1
        self._entry_peso_manual.grid_remove()

        # Captura explícita -- el peso no se toma en silencio al guardar:
        # el operador tiene que confirmar con este botón que el peso en
        # pantalla es el correcto (igual criterio que "CAPTURAR PESO" en
        # Salida). "GUARDAR Y COMPLETAR" usa el valor ya capturado acá,
        # no vuelve a leer la báscula por su cuenta.
        boton_primario(
            self._form_frame, "⚖  CAPTURAR PESO FINAL",
            command=self._capturar_peso_final, height=42,
        ).grid(row=row, column=0, sticky="ew", pady=(0, 4)); row += 1

        self._lbl_peso_final_capturado = ctk.CTkLabel(
            self._form_frame, text="Todavía no se capturó el peso final.",
            font=ctk.CTkFont(family=UI["fuente"], size=11, weight="bold"),
            text_color=UI["color_muted"]
        )
        self._lbl_peso_final_capturado.grid(row=row, column=0, pady=(0, 10)); row += 1

        # Separador
        ctk.CTkFrame(self._form_frame, height=1,
                      fg_color=UI["color_border"]).grid(
            row=row, column=0, sticky="ew", pady=10); row += 1

        etiqueta_campo(self._form_frame, "Complete los datos finales").grid(
            row=row, column=0, sticky="w", pady=(0, 8)); row += 1

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
        boton_primario(
            self._form_frame, "💾  GUARDAR Y COMPLETAR",
            command=self._completar, height=50,
        ).grid(row=row, column=0, sticky="ew"); row += 1

        # Reinicia el polling de peso final -- si ya había uno corriendo
        # (el operador seleccionó otra pesada sin navegar de pantalla), se
        # cancela antes de arrancar uno nuevo para no acumular timers.
        if self._after_id_peso_final is not None:
            self.after_cancel(self._after_id_peso_final)
            self._after_id_peso_final = None
        self._actualizar_peso_final()

    # ----------------------------------------------------------
    def _toggle_peso_manual(self):
        """Muestra/oculta el campo de peso manual según el checkbox."""
        if self._peso_manual_var.get():
            self._entry_peso_manual.grid()
            self._entry_peso_manual.focus()
        else:
            self._entry_peso_manual.grid_remove()

    def _obtener_peso(self) -> float:
        """Peso tipeado a mano si está marcado el checkbox, o el de la báscula."""
        if self._peso_manual_var.get():
            try:
                return float(self._entry_peso_manual.get().strip().replace(",", "."))
            except (ValueError, AttributeError):
                return 0.0
        try:
            return leer_peso_actual() or 0.0
        except Exception:
            return 0.0

    # ----------------------------------------------------------
    def _actualizar_peso_final(self):
        """Lee en vivo el peso de la báscula para el peso final (3er pesaje)."""
        if not self._pesada_seleccionada:
            return
        if not hasattr(self, "_lbl_peso_final"):
            return

        try:
            peso = leer_peso_actual() or 0.0
            self._lbl_peso_final.configure(text=f"{peso:,.0f} KG")

            if peso > 0:
                bruto_prepesaje = float(self._pesada_seleccionada["peso_bruto"] or 0)
                dif = peso - bruto_prepesaje
                self._lbl_dif_peso_final.configure(
                    text=f"Diferencia vs. pre-pesaje ({bruto_prepesaje:,.0f} KG): {dif:+,.0f} KG",
                    text_color=UI["color_muted"] if abs(dif) < 1 else UI["color_warning"]
                )
        except Exception:
            pass

        # 0.5s: ver comentario equivalente en pesaje_entrada_view.py
        # (hallazgo C-04 -- leer_peso_actual() ya no bloquea).
        self._after_id_peso_final = self.after(250, self._actualizar_peso_final)

    # ----------------------------------------------------------
    def _capturar_peso_final(self):
        """Confirma el peso final mostrado en pantalla -- captura explícita,
        no se toma en silencio al completar (mismo criterio que Salida)."""
        if not self._pesada_seleccionada:
            return

        peso = self._obtener_peso()

        if peso <= 0:
            if self._peso_manual_var.get():
                messagebox.showerror("Sin peso", "Ingrese un peso manual válido (mayor a 0).")
            else:
                messagebox.showerror("Sin peso",
                    "No hay un peso válido en la báscula.\n"
                    "Asegúrese de que el vehículo esté sobre la báscula.\n\n"
                    "Si la báscula no responde, puede tildar \"Ingresar peso manualmente\".")
            return

        # Hallazgo I-03: el peso final ya no se puede capturar mientras
        # todavía está oscilando. No aplica al peso manual.
        if not self._peso_manual_var.get() and not es_peso_estable():
            messagebox.showerror("Peso inestable",
                "El peso todavía se está estabilizando.\n"
                "Espere a que el indicador diga \"PESO ESTABLE\" antes de capturar.")
            return

        self._peso_final_capturado = float(peso)
        self._peso_final_es_manual = self._peso_manual_var.get()
        self._lbl_peso_final_capturado.configure(
            text=f"✓ Peso final capturado: {peso:,.0f} KG" +
                 (" (manual)" if self._peso_final_es_manual else ""),
            text_color=UI["color_success"]
        )

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

        if self._peso_final_capturado is None:
            messagebox.showerror("Falta capturar el peso",
                "Debe capturar el peso final (botón '⚖ CAPTURAR PESO FINAL') "
                "antes de completar la pesada.")
            return

        peso_final = self._peso_final_capturado

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
            peso_final=float(peso_final),
            orden_compra=orden,
            cantidad=cantidad,
            precintos=precintos,
            observaciones=obs,
            es_manual=self._peso_final_es_manual,
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
                    f"Neto: {float(pesada['peso_neto'] or 0):,.0f} KG\n"
                    f"Peso final: {float(pesada['peso_final'] or 0):,.0f} KG\n\n"
                    "El camión ya tiene el okey para salir.\n\n"
                    "¿Abrir el ticket PDF?"
                ):
                    os.startfile(ruta_pdf)
            except (ApiError, OSError):
                messagebox.showinfo(
                    "Completado ✓",
                    f"Pesada {pesada['numero_ticket']} completada.\n"
                    f"Neto: {float(pesada['peso_neto'] or 0):,.0f} KG\n"
                    f"Peso final: {float(pesada['peso_final'] or 0):,.0f} KG\n\n"
                    "El camión ya tiene el okey para salir."
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
        self._peso_final_capturado = None
