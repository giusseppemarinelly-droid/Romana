# ============================================================
# gui/pesaje/pesaje_entrada_view.py — Registro de Entrada
# ============================================================

import customtkinter as ctk
from tkinter import messagebox
from config import UI
from services.pesaje_service import (
    registrar_entrada, buscar_vehiculo_por_placa,
    listar_vehiculos_activos, listar_conductores_activos,
    listar_productos_por_tipo
)
from hardware.display_manager import leer_peso_actual, es_peso_estable


TIPO_PESAJE_OPCIONES = ["PESAJE GENERAL", "PRODUCTO TERMINADO"]


class PesajeEntradaView(ctk.CTkFrame):
    """Pantalla de registro de entrada de camión a la báscula."""

    def __init__(self, parent, callback_navegar=None):
        super().__init__(parent, fg_color="transparent")
        self.callback_navegar = callback_navegar
        self._vehiculo_seleccionado = None
        self._conductor_seleccionado = None
        self._productos_cache = []
        self._construir()
        self._actualizar_peso()

    # ----------------------------------------------------------
    def _construir(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Título ───────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=UI["color_card"],
                               border_color=UI["color_border"],
                               border_width=1, corner_radius=10)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header, text="⬇  REGISTRO DE ENTRADA",
            font=ctk.CTkFont(family=UI["fuente"], size=16, weight="bold"),
            text_color=UI["color_accent"]
        ).grid(row=0, column=0, padx=20, pady=15, sticky="w")

        ctk.CTkLabel(
            header,
            text="Complete los datos y capture el peso de la báscula.",
            font=ctk.CTkFont(family=UI["fuente"], size=12),
            text_color=UI["color_muted"]
        ).grid(row=0, column=1, padx=5, pady=15, sticky="w")

        # ── Cuerpo con dos columnas ──────────────────────────
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=20, pady=5)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)

        self._construir_formulario(body)
        self._construir_panel_peso(body)

    # ----------------------------------------------------------
    def _construir_formulario(self, parent):
        """Panel izquierdo — campos del formulario."""
        card = ctk.CTkFrame(parent, fg_color=UI["color_card"],
                             border_color=UI["color_border"],
                             border_width=1, corner_radius=12)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=10)
        card.grid_columnconfigure((0, 1), weight=1)

        row = 0

        # ── Tipo de pesaje ────────────────────────────────────
        self._seccion(card, "TIPO DE PESAJE", row); row += 1

        self._tipo_var = ctk.StringVar(value="PESAJE GENERAL")
        tipo_frame = ctk.CTkFrame(card, fg_color="transparent")
        tipo_frame.grid(row=row, column=0, columnspan=2, sticky="ew",
                        padx=18, pady=(4, 10))

        for texto in TIPO_PESAJE_OPCIONES:
            ctk.CTkRadioButton(
                tipo_frame,
                text=texto,
                variable=self._tipo_var,
                value=texto,
                command=self._on_tipo_changed,
                font=ctk.CTkFont(family=UI["fuente"], size=13),
                fg_color=UI["color_accent"]
            ).pack(side="left", padx=(0, 20))
        row += 1

        # ── Producto ──────────────────────────────────────────
        self._seccion(card, "PRODUCTO", row); row += 1

        prod_frame = ctk.CTkFrame(card, fg_color="transparent")
        prod_frame.grid(row=row, column=0, columnspan=2, sticky="ew",
                        padx=18, pady=(4, 10))
        prod_frame.grid_columnconfigure(1, weight=1)

        self._lbl_cod_prod = ctk.CTkLabel(
            prod_frame, text="—",
            font=ctk.CTkFont(family=UI["fuente"], size=13, weight="bold"),
            text_color=UI["color_accent"],
            width=50, anchor="center"
        )
        self._lbl_cod_prod.grid(row=0, column=0, padx=(0, 8))

        self._combo_producto = ctk.CTkComboBox(
            prod_frame,
            values=["-- Seleccione --"],
            command=self._on_producto_changed,
            height=36,
            font=ctk.CTkFont(family=UI["fuente"], size=13)
        )
        self._combo_producto.grid(row=0, column=1, sticky="ew")
        self._combo_producto.set("-- Seleccione --")
        row += 1

        # ── Vehículo ──────────────────────────────────────────
        self._seccion(card, "VEHÍCULO", row); row += 1

        veh_frame = ctk.CTkFrame(card, fg_color="transparent")
        veh_frame.grid(row=row, column=0, columnspan=2, sticky="ew",
                        padx=18, pady=(4, 10))
        veh_frame.grid_columnconfigure(0, weight=1)

        self._combo_vehiculo = ctk.CTkComboBox(
            veh_frame,
            values=["-- Seleccione o escriba placa --"],
            height=36,
            font=ctk.CTkFont(family=UI["fuente"], size=13)
        )
        self._combo_vehiculo.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            veh_frame, text="🔍 Buscar",
            command=self._buscar_vehiculo,
            width=90, height=36,
            fg_color=UI["color_accent"],
            hover_color=UI["color_accent_hover"],
            font=ctk.CTkFont(family=UI["fuente"], size=12)
        ).grid(row=0, column=1)

        self._lbl_vehiculo_info = ctk.CTkLabel(
            card, text="",
            font=ctk.CTkFont(family=UI["fuente"], size=11),
            text_color=UI["color_muted"]
        )
        self._lbl_vehiculo_info.grid(row=row + 1, column=0, columnspan=2,
                                      padx=18, pady=(0, 6), sticky="w")
        row += 2

        # Cargar vehículos en el combo
        vehiculos = listar_vehiculos_activos()
        self._vehiculos_map = {v.placa: v for v in vehiculos}
        self._combo_vehiculo.configure(
            values=["-- Seleccione --"] + [v.placa for v in vehiculos]
        )
        self._combo_vehiculo.set("-- Seleccione --")
        self._combo_vehiculo.configure(command=self._on_vehiculo_changed)

        # ── Conductor ─────────────────────────────────────────
        self._seccion(card, "CONDUCTOR", row); row += 1

        cond_frame = ctk.CTkFrame(card, fg_color="transparent")
        cond_frame.grid(row=row, column=0, columnspan=2, sticky="ew",
                         padx=18, pady=(4, 10))
        cond_frame.grid_columnconfigure((0, 1), weight=1)

        self._entry_cedula = ctk.CTkEntry(
            cond_frame, placeholder_text="Cédula / Documento",
            height=36, font=ctk.CTkFont(family=UI["fuente"], size=13)
        )
        self._entry_cedula.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self._entry_nombre_conductor = ctk.CTkEntry(
            cond_frame, placeholder_text="Nombre del conductor",
            height=36, font=ctk.CTkFont(family=UI["fuente"], size=13)
        )
        self._entry_nombre_conductor.grid(row=0, column=1, sticky="ew")
        row += 1

        # ── Empresa Transportista ─────────────────────────────
        self._seccion(card, "EMPRESA TRANSPORTISTA", row); row += 1
        self._entry_transportista = ctk.CTkEntry(
            card, placeholder_text="Nombre de la empresa transportista",
            height=36, font=ctk.CTkFont(family=UI["fuente"], size=13)
        )
        self._entry_transportista.grid(row=row, column=0, columnspan=2,
                                        sticky="ew", padx=18, pady=(4, 10))
        row += 1

        # ── Empresa Cliente / Proveedor ───────────────────────
        self._seccion(card, "EMPRESA (CLIENTE O PROVEEDOR)", row); row += 1
        self._entry_empresa_cp = ctk.CTkEntry(
            card, placeholder_text="Nombre de la empresa cliente o proveedor",
            height=36, font=ctk.CTkFont(family=UI["fuente"], size=13)
        )
        self._entry_empresa_cp.grid(row=row, column=0, columnspan=2,
                                     sticky="ew", padx=18, pady=(4, 18))
        row += 1

        # Cargar productos por defecto (GENERAL)
        self._cargar_productos("GENERAL")

    # ----------------------------------------------------------
    def _construir_panel_peso(self, parent):
        """Panel derecho — báscula y botón registrar."""
        panel = ctk.CTkFrame(parent, fg_color="transparent")
        panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=10)
        panel.grid_columnconfigure(0, weight=1)

        # ── Peso en vivo ──────────────────────────────────────
        bascula_card = ctk.CTkFrame(panel, fg_color=UI["color_card"],
                                     border_color=UI["color_border"],
                                     border_width=1, corner_radius=12)
        bascula_card.grid(row=0, column=0, sticky="ew")
        bascula_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            bascula_card, text="⚖  PESO BÁSCULA",
            font=ctk.CTkFont(family=UI["fuente"], size=12, weight="bold"),
            text_color=UI["color_muted"]
        ).grid(row=0, column=0, padx=16, pady=(16, 4))

        self._lbl_peso = ctk.CTkLabel(
            bascula_card, text="--- KG",
            font=ctk.CTkFont(family=UI["fuente"], size=36, weight="bold"),
            text_color=UI["color_accent"]
        )
        self._lbl_peso.grid(row=1, column=0, padx=16, pady=4)

        self._lbl_estable = ctk.CTkLabel(
            bascula_card, text="● En espera...",
            font=ctk.CTkFont(family=UI["fuente"], size=12),
            text_color=UI["color_muted"]
        )
        self._lbl_estable.grid(row=2, column=0, padx=16, pady=4)

        ctk.CTkButton(
            bascula_card, text="↻  Actualizar peso",
            command=self._actualizar_peso,
            height=34, fg_color="transparent",
            border_color=UI["color_accent"], border_width=1,
            text_color=UI["color_accent"],
            hover_color=UI["color_bg"],
            font=ctk.CTkFont(family=UI["fuente"], size=12)
        ).grid(row=3, column=0, padx=16, pady=(4, 16), sticky="ew")

        # ── Resumen ───────────────────────────────────────────
        resumen_card = ctk.CTkFrame(panel, fg_color=UI["color_card"],
                                     border_color=UI["color_border"],
                                     border_width=1, corner_radius=12)
        resumen_card.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        resumen_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            resumen_card, text="RESUMEN",
            font=ctk.CTkFont(family=UI["fuente"], size=11, weight="bold"),
            text_color=UI["color_muted"]
        ).grid(row=0, column=0, padx=16, pady=(14, 4), sticky="w")

        self._lbl_resumen_tipo = ctk.CTkLabel(
            resumen_card, text="Tipo: —",
            font=ctk.CTkFont(family=UI["fuente"], size=12),
            text_color=UI["color_text"]
        )
        self._lbl_resumen_tipo.grid(row=1, column=0, padx=16, pady=2, sticky="w")

        self._lbl_resumen_prod = ctk.CTkLabel(
            resumen_card, text="Producto: —",
            font=ctk.CTkFont(family=UI["fuente"], size=12),
            text_color=UI["color_text"]
        )
        self._lbl_resumen_prod.grid(row=2, column=0, padx=16, pady=2, sticky="w")

        self._lbl_resumen_veh = ctk.CTkLabel(
            resumen_card, text="Vehículo: —",
            font=ctk.CTkFont(family=UI["fuente"], size=12),
            text_color=UI["color_text"]
        )
        self._lbl_resumen_veh.grid(row=3, column=0, padx=16, pady=(2, 14), sticky="w")

        # ── Botón registrar ───────────────────────────────────
        ctk.CTkButton(
            panel,
            text="⬇  REGISTRAR ENTRADA",
            command=self._registrar,
            height=56,
            font=ctk.CTkFont(family=UI["fuente"], size=15, weight="bold"),
            fg_color=UI["color_accent"],
            hover_color=UI["color_accent_hover"],
            corner_radius=10
        ).grid(row=2, column=0, sticky="ew", pady=(12, 0))

    # ----------------------------------------------------------
    def _seccion(self, parent, texto, row):
        """Etiqueta de sección dentro del formulario."""
        ctk.CTkLabel(
            parent, text=texto,
            font=ctk.CTkFont(family=UI["fuente"], size=10, weight="bold"),
            text_color=UI["color_muted"]
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=18, pady=(12, 0))

    # ----------------------------------------------------------
    def _cargar_productos(self, tipo: str):
        """Carga la lista de productos según el tipo de pesaje."""
        self._productos_cache = listar_productos_por_tipo(tipo)
        nombres = [f"{p.codigo} — {p.nombre}" for p in self._productos_cache]
        self._combo_producto.configure(
            values=["-- Seleccione --"] + nombres
        )
        self._combo_producto.set("-- Seleccione --")
        self._lbl_cod_prod.configure(text="—")

    # ----------------------------------------------------------
    def _on_tipo_changed(self):
        tipo_raw = self._tipo_var.get()
        tipo_key = "GENERAL" if tipo_raw == "PESAJE GENERAL" else "PRODUCTO_TERMINADO"
        self._cargar_productos(tipo_key)
        self._lbl_resumen_tipo.configure(text=f"Tipo: {tipo_raw}")

    # ----------------------------------------------------------
    def _on_producto_changed(self, seleccion):
        if seleccion == "-- Seleccione --" or not seleccion:
            self._lbl_cod_prod.configure(text="—")
            self._lbl_resumen_prod.configure(text="Producto: —")
            return
        # Extraer código del texto "002 — Chatarra"
        codigo = seleccion.split(" — ")[0]
        self._lbl_cod_prod.configure(text=codigo)
        nombre = seleccion.split(" — ")[1] if " — " in seleccion else seleccion
        self._lbl_resumen_prod.configure(text=f"Producto: {nombre}")

    # ----------------------------------------------------------
    def _on_vehiculo_changed(self, seleccion):
        if seleccion == "-- Seleccione --":
            self._vehiculo_seleccionado = None
            self._lbl_vehiculo_info.configure(text="")
            self._lbl_resumen_veh.configure(text="Vehículo: —")
            return
        v = self._vehiculos_map.get(seleccion)
        if v:
            self._vehiculo_seleccionado = v
            tara = f"{float(v.tara_registrada):,.0f}" if v.tara_registrada else "N/A"
            self._lbl_vehiculo_info.configure(
                text=f"{v.descripcion or ''}  |  Tara registrada: {tara} KG"
            )
            self._lbl_resumen_veh.configure(text=f"Vehículo: {seleccion}")

    # ----------------------------------------------------------
    def _buscar_vehiculo(self):
        placa = self._combo_vehiculo.get().strip().upper()
        if not placa or placa == "-- SELECCIONE --":
            messagebox.showwarning("Buscar", "Ingrese o seleccione una placa")
            return
        v = self._vehiculos_map.get(placa)
        if v:
            self._vehiculo_seleccionado = v
            tara = f"{float(v.tara_registrada):,.0f}" if v.tara_registrada else "N/A"
            self._lbl_vehiculo_info.configure(
                text=f"{v.descripcion or ''}  |  Tara: {tara} KG"
            )
            self._lbl_resumen_veh.configure(text=f"Vehículo: {v.placa}")
        else:
            messagebox.showinfo("No encontrado",
                f"Placa '{placa}' no está registrada.\n"
                "Puede continuar con esta placa o registrarla primero en Maestros → Vehículos.")

    # ----------------------------------------------------------
    def _actualizar_peso(self):
        """Lee el peso de la báscula y actualiza la pantalla."""
        try:
            peso = leer_peso_actual()
            if peso is not None:
                self._lbl_peso.configure(text=f"{peso:,.0f} KG")
                if es_peso_estable():
                    self._lbl_estable.configure(
                        text="● Peso ESTABLE", text_color=UI["color_success"])
                else:
                    self._lbl_estable.configure(
                        text="⟳ Estabilizando...", text_color="#f59e0b")
            else:
                self._lbl_peso.configure(text="--- KG")
                self._lbl_estable.configure(
                    text="Sin señal", text_color=UI["color_muted"])
        except Exception:
            self._lbl_peso.configure(text="ERROR")

        # Auto-refrescar cada 3 segundos
        self.after(3000, self._actualizar_peso)

    # ----------------------------------------------------------
    def _registrar(self):
        """Valida y registra la entrada del camión."""
        # Peso
        try:
            peso = leer_peso_actual() or 0.0
        except Exception:
            peso = 0.0

        if peso <= 0:
            messagebox.showerror("Sin peso",
                "No hay un peso válido en la báscula.\n"
                "Asegúrese de que el vehículo esté sobre la báscula y el peso esté estable.")
            return

        # Vehículo
        placa_raw = self._combo_vehiculo.get().strip()
        if not placa_raw or placa_raw == "-- Seleccione --":
            messagebox.showerror("Validación", "Debe seleccionar o ingresar la placa del vehículo.")
            return

        # Si el vehículo no está en el mapa, lo buscamos o pedimos registrarlo
        vehiculo = self._vehiculo_seleccionado
        if vehiculo is None:
            from services.pesaje_service import buscar_vehiculo_por_placa
            vehiculo = buscar_vehiculo_por_placa(placa_raw)
            if vehiculo is None:
                if not messagebox.askyesno("Vehículo no registrado",
                    f"La placa '{placa_raw.upper()}' no está en el sistema.\n\n"
                    "¿Desea continuar de todas formas?\n"
                    "(El vehículo quedará pendiente de registro en Maestros)"):
                    return
                # Crear vehículo temporal
                from database.engine import SessionLocal
                from database.models import Vehiculo
                db = SessionLocal()
                try:
                    veh_tmp = Vehiculo(
                        placa=placa_raw.upper(),
                        descripcion="Registrado automáticamente",
                        tara_registrada=0,
                        tipo="camion"
                    )
                    db.add(veh_tmp)
                    db.commit()
                    db.refresh(veh_tmp)
                    vehiculo = veh_tmp
                finally:
                    db.close()

        # Tipo de pesaje
        tipo_raw = self._tipo_var.get()
        tipo_key = "GENERAL" if tipo_raw == "PESAJE GENERAL" else "PRODUCTO_TERMINADO"

        # Producto
        prod_sel = self._combo_producto.get()
        producto_id = None
        if prod_sel and prod_sel != "-- Seleccione --":
            codigo_sel = prod_sel.split(" — ")[0]
            for p in self._productos_cache:
                if p.codigo == codigo_sel:
                    producto_id = p.id
                    break

        resultado = registrar_entrada(
            peso_bruto=float(peso),
            vehiculo_id=vehiculo.id,
            tipo_pesaje=tipo_key,
            producto_id=producto_id,
            empresa_transportista=self._entry_transportista.get().strip(),
            empresa_cliente_proveedor=self._entry_empresa_cp.get().strip(),
            cedula_conductor_libre=self._entry_cedula.get().strip(),
            observaciones=""
        )

        if resultado["exito"]:
            messagebox.showinfo(
                "Entrada Registrada ✓",
                f"Ticket: {resultado['ticket']}\n"
                f"Vehículo: {placa_raw.upper()}\n"
                f"Peso entrada: {peso:,.0f} KG\n\n"
                "El camión quedó registrado en cola.\n"
                "Cuando regrese cargado, use 'Salida' para capturar el 2° peso."
            )
            self._limpiar_formulario()
        else:
            messagebox.showerror("Error al registrar", resultado["mensaje"])

    # ----------------------------------------------------------
    def _limpiar_formulario(self):
        self._tipo_var.set("PESAJE GENERAL")
        self._cargar_productos("GENERAL")
        self._combo_vehiculo.set("-- Seleccione --")
        self._vehiculo_seleccionado = None
        self._lbl_vehiculo_info.configure(text="")
        self._entry_cedula.delete(0, "end")
        self._entry_nombre_conductor.delete(0, "end")
        self._entry_transportista.delete(0, "end")
        self._entry_empresa_cp.delete(0, "end")
        self._lbl_resumen_tipo.configure(text="Tipo: —")
        self._lbl_resumen_prod.configure(text="Producto: —")
        self._lbl_resumen_veh.configure(text="Vehículo: —")
