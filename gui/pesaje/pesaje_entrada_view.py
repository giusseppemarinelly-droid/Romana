# ============================================================
# gui/pesaje/pesaje_entrada_view.py — Registro de Entrada
# ============================================================

import customtkinter as ctk
from tkinter import messagebox
from config import UI
from client.api_client import api_client, ApiError
from hardware.display_manager import leer_peso_actual, es_peso_estable
from gui.async_utils import cargar_en_hilo


TIPO_PESAJE_OPCIONES = ["PESAJE GENERAL", "PRODUCTO TERMINADO"]

# Estilo compartido de campos de entrada — fondo levemente distinto de
# la tarjeta (color_input_bg) y borde de 2px, para que se noten como
# "editables" en vez del recuadro plano que traía CTk por defecto.
_INPUT_STYLE = dict(
    fg_color=UI["color_input_bg"],
    border_color=UI["color_border"],
    border_width=2,
    corner_radius=8,
)
_COMBO_STYLE = dict(
    _INPUT_STYLE,
    button_color=UI["color_accent"],
    button_hover_color=UI["color_accent_hover"],
    dropdown_fg_color=UI["color_card"],
    dropdown_hover_color=UI["color_bg"],
    dropdown_text_color=UI["color_text"],
)


class PesajeEntradaView(ctk.CTkFrame):
    """Pantalla de registro de entrada de camión a la báscula."""

    def __init__(self, parent, callback_navegar=None):
        super().__init__(parent, fg_color="transparent")
        self.callback_navegar = callback_navegar
        self._vehiculo_seleccionado = None
        self._conductor_seleccionado = None
        self._productos_cache = []
        self._after_id_peso = None
        self._construir()
        self._actualizar_peso()

    def destroy(self):
        # _actualizar_peso() se reprograma solo con self.after() cada
        # 3s -- sin cancelarlo acá, al navegar a otra pantalla (que
        # destruye este frame) el timer sigue vivo para siempre, leyendo
        # la báscula cada 3s contra widgets ya destruidos. Cada visita a
        # esta pantalla dejaba un timer fantasma más corriendo de fondo,
        # y con varios acumulados se sentían pausas al navegar.
        if self._after_id_peso is not None:
            self.after_cancel(self._after_id_peso)
            self._after_id_peso = None
        super().destroy()

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
            header, text="↓  REGISTRO DE ENTRADA",
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
                fg_color=UI["color_accent"],
                hover_color=UI["color_accent_hover"],
                border_color=UI["color_border"],
                radiobutton_width=20,
                radiobutton_height=20,
                border_width_checked=6,
            ).pack(side="left", padx=(0, 24))
        row += 1

        # ── Producto ──────────────────────────────────────────
        self._seccion(card, "PRODUCTO", row); row += 1

        prod_frame = ctk.CTkFrame(card, fg_color="transparent")
        prod_frame.grid(row=row, column=0, columnspan=2, sticky="ew",
                        padx=18, pady=(4, 10))
        prod_frame.grid_columnconfigure(1, weight=1)

        # Badge con el código del producto — chip azul claro en vez de
        # texto plano, para que se lea como un dato "vivo" del formulario.
        self._lbl_cod_prod = ctk.CTkLabel(
            prod_frame, text="—",
            font=ctk.CTkFont(family=UI["fuente"], size=13, weight="bold"),
            text_color=UI["color_accent"],
            fg_color="#dbeafe", corner_radius=8,
            width=50, height=40, anchor="center"
        )
        self._lbl_cod_prod.grid(row=0, column=0, padx=(0, 8))

        self._combo_producto = ctk.CTkComboBox(
            prod_frame,
            values=["-- Seleccione --"],
            command=self._on_producto_changed,
            height=40,
            font=ctk.CTkFont(family=UI["fuente"], size=13),
            **_COMBO_STYLE,
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
            height=40,
            font=ctk.CTkFont(family=UI["fuente"], size=13),
            **_COMBO_STYLE,
        )
        self._combo_vehiculo.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            veh_frame, text="🔍 Buscar",
            command=self._buscar_vehiculo,
            width=96, height=40, corner_radius=8,
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

        # Vehículos se cargan en segundo plano (_cargar_vehiculos) para no
        # bloquear la ventana mientras arranca esta pantalla -- ver
        # gui/async_utils.py.
        self._vehiculos_map = {}
        self._combo_vehiculo.configure(command=self._on_vehiculo_changed)
        self._cargar_vehiculos()

        # ── Conductor ─────────────────────────────────────────
        # Mismo patrón que Vehículo: se escribe la cédula, se busca contra
        # el maestro de conductores (ILIKE sobre documento/nombre en el
        # backend) y si existe se autocompleta el nombre y queda linkeado
        # por conductor_id (mejor para kardex/reportes); si no existe,
        # sigue funcionando como texto libre (cedula_conductor_libre).
        self._seccion(card, "CONDUCTOR", row); row += 1

        cond_frame = ctk.CTkFrame(card, fg_color="transparent")
        cond_frame.grid(row=row, column=0, columnspan=2, sticky="ew",
                         padx=18, pady=(4, 6))
        cond_frame.grid_columnconfigure(0, weight=1)

        self._entry_cedula = ctk.CTkEntry(
            cond_frame, placeholder_text="Cédula / Documento",
            height=40, font=ctk.CTkFont(family=UI["fuente"], size=13),
            **_INPUT_STYLE,
        )
        self._entry_cedula.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._entry_cedula.bind("<Return>", lambda e: self._buscar_conductor())

        ctk.CTkButton(
            cond_frame, text="🔍 Buscar",
            command=self._buscar_conductor,
            width=96, height=40, corner_radius=8,
            fg_color=UI["color_accent"],
            hover_color=UI["color_accent_hover"],
            font=ctk.CTkFont(family=UI["fuente"], size=12)
        ).grid(row=0, column=1)
        row += 1

        self._entry_nombre_conductor = ctk.CTkEntry(
            card, placeholder_text="Nombre del conductor",
            height=40, font=ctk.CTkFont(family=UI["fuente"], size=13),
            **_INPUT_STYLE,
        )
        self._entry_nombre_conductor.grid(row=row, column=0, columnspan=2,
                                           sticky="ew", padx=18, pady=(0, 4))
        row += 1

        self._lbl_conductor_info = ctk.CTkLabel(
            card, text="",
            font=ctk.CTkFont(family=UI["fuente"], size=11),
            text_color=UI["color_muted"]
        )
        self._lbl_conductor_info.grid(row=row, column=0, columnspan=2,
                                       padx=18, pady=(0, 6), sticky="w")
        row += 1

        # ── Empresa Transportista ─────────────────────────────
        self._seccion(card, "EMPRESA TRANSPORTISTA", row); row += 1
        self._entry_transportista = ctk.CTkEntry(
            card, placeholder_text="Nombre de la empresa transportista",
            height=40, font=ctk.CTkFont(family=UI["fuente"], size=13),
            **_INPUT_STYLE,
        )
        self._entry_transportista.grid(row=row, column=0, columnspan=2,
                                        sticky="ew", padx=18, pady=(4, 10))
        row += 1

        # ── Empresa Cliente / Proveedor ───────────────────────
        self._seccion(card, "EMPRESA (CLIENTE O PROVEEDOR)", row); row += 1
        self._entry_empresa_cp = ctk.CTkEntry(
            card, placeholder_text="Nombre de la empresa cliente o proveedor",
            height=40, font=ctk.CTkFont(family=UI["fuente"], size=13),
            **_INPUT_STYLE,
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
            font=ctk.CTkFont(family=UI["fuente"], size=40, weight="bold"),
            text_color=UI["color_accent"]
        )
        self._lbl_peso.grid(row=1, column=0, padx=16, pady=4)

        # Pill de estado — mismo patrón visual que el badge de rol del
        # header (fondo de color + texto), en vez de solo un punto de
        # color suelto.
        self._lbl_estable = ctk.CTkLabel(
            bascula_card, text="●  En espera...",
            font=ctk.CTkFont(family=UI["fuente"], size=12, weight="bold"),
            text_color=UI["color_muted"],
            fg_color=UI["color_bg"], corner_radius=6,
            width=160, height=26,
        )
        self._lbl_estable.grid(row=2, column=0, padx=16, pady=6)

        ctk.CTkButton(
            bascula_card, text="↻  Actualizar peso",
            command=self._actualizar_peso,
            height=36, corner_radius=8, fg_color="transparent",
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
            text="↓  REGISTRAR ENTRADA",
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
    def _cargar_vehiculos(self):
        cargar_en_hilo(
            self, lambda: api_client.listar_maestro("vehiculos"),
            on_exito=self._on_vehiculos_cargados,
            on_error=lambda e: messagebox.showerror("Error de conexión", str(e)),
        )

    def _on_vehiculos_cargados(self, vehiculos):
        self._vehiculos_map = {v["placa"]: v for v in vehiculos}
        self._combo_vehiculo.configure(
            values=["-- Seleccione --"] + [v["placa"] for v in vehiculos]
        )
        self._combo_vehiculo.set("-- Seleccione --")

    # ----------------------------------------------------------
    def _cargar_productos(self, tipo: str):
        """Carga la lista de productos según el tipo de pesaje.

        El filtro por tipo_pesaje se hace en memoria (no hay endpoint
        dedicado): el catálogo de productos es chico, a diferencia del
        buscador de vehículos/conductores que sí necesitaba búsqueda
        indexada en servidor.
        """
        cargar_en_hilo(
            self, lambda: api_client.listar_maestro("productos"),
            on_exito=lambda todos: self._on_productos_cargados(todos, tipo),
            on_error=lambda e: messagebox.showerror("Error de conexión", str(e)),
        )

    def _on_productos_cargados(self, todos, tipo):
        self._productos_cache = [p for p in todos if p["tipo_pesaje"] == tipo]
        nombres = [f"{p['codigo']} — {p['nombre']}" for p in self._productos_cache]
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
            tara = f"{float(v['tara_registrada']):,.0f}" if v["tara_registrada"] else "N/A"
            self._lbl_vehiculo_info.configure(
                text=f"{v['descripcion'] or ''}  |  Tara registrada: {tara} KG"
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
            tara = f"{float(v['tara_registrada']):,.0f}" if v["tara_registrada"] else "N/A"
            self._lbl_vehiculo_info.configure(
                text=f"{v['descripcion'] or ''}  |  Tara: {tara} KG"
            )
            self._lbl_resumen_veh.configure(text=f"Vehículo: {v['placa']}")
        else:
            messagebox.showinfo("No encontrado",
                f"Placa '{placa}' no está registrada.\n"
                "Puede continuar con esta placa o registrarla primero en Maestros → Vehículos.")

    # ----------------------------------------------------------
    def _buscar_conductor(self):
        """Busca el conductor por cédula contra el maestro (igual que Vehículo).

        Si existe, autocompleta el nombre y lo deja linkeado por
        conductor_id (mejor para kardex/reportes). Si no existe, el
        operador puede seguir escribiendo el nombre a mano -- se guarda
        como texto libre (cedula_conductor_libre), igual que antes.
        """
        cedula = self._entry_cedula.get().strip()
        if not cedula:
            messagebox.showwarning("Buscar", "Ingrese la cédula o documento del conductor")
            return

        self._conductor_seleccionado = None
        try:
            encontrados = api_client.listar_maestro("conductores", search=cedula)
        except ApiError as e:
            messagebox.showerror("Error de conexión", str(e))
            return

        cedula_norm = cedula.upper().replace(" ", "")
        c = next(
            (x for x in encontrados
             if x["documento"].upper().replace(" ", "") == cedula_norm),
            None
        )

        if c:
            self._conductor_seleccionado = c
            self._entry_nombre_conductor.delete(0, "end")
            self._entry_nombre_conductor.insert(0, c["nombre"])
            self._lbl_conductor_info.configure(
                text=f"✓ Conductor registrado  |  {c.get('telefono') or 'sin teléfono'}",
                text_color=UI["color_success"]
            )
        else:
            self._lbl_conductor_info.configure(
                text="Conductor no registrado — se guardará solo con la cédula ingresada.",
                text_color=UI["color_muted"]
            )

    # ----------------------------------------------------------
    def _actualizar_peso(self):
        """Lee el peso de la báscula y actualiza la pantalla."""
        try:
            peso = leer_peso_actual()
            if peso is not None:
                self._lbl_peso.configure(text=f"{peso:,.0f} KG")
                if es_peso_estable():
                    self._lbl_estable.configure(
                        text="●  PESO ESTABLE", text_color=UI["color_success"],
                        fg_color="#d1fae5")
                else:
                    self._lbl_estable.configure(
                        text="↻  Estabilizando...", text_color="#b45309",
                        fg_color="#fef3c7")
            else:
                self._lbl_peso.configure(text="--- KG")
                self._lbl_estable.configure(
                    text="●  Sin señal", text_color=UI["color_muted"],
                    fg_color=UI["color_bg"])
        except Exception:
            self._lbl_peso.configure(text="ERROR")

        # Auto-refrescar cada 3 segundos
        self._after_id_peso = self.after(3000, self._actualizar_peso)

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
            try:
                encontrados = api_client.listar_maestro("vehiculos", search=placa_raw)
            except ApiError as e:
                messagebox.showerror("Error de conexión", str(e))
                return
            vehiculo = next((v for v in encontrados if v["placa"] == placa_raw.upper()), None)
            if vehiculo is None:
                if not messagebox.askyesno("Vehículo no registrado",
                    f"La placa '{placa_raw.upper()}' no está en el sistema.\n\n"
                    "¿Desea continuar de todas formas?\n"
                    "(El vehículo quedará pendiente de registro en Maestros)"):
                    return
                # Crear vehículo temporal
                resultado_veh = api_client.autoregistrar_vehiculo({
                    "placa": placa_raw.upper(),
                    "descripcion": "Registrado automáticamente",
                    "tara_registrada": 0,
                    "tipo": "camion",
                    "proveedor_id": None,
                })
                if not resultado_veh["exito"]:
                    messagebox.showerror("Error", resultado_veh["mensaje"])
                    return
                vehiculo = resultado_veh["data"]

        # Tipo de pesaje
        tipo_raw = self._tipo_var.get()
        tipo_key = "GENERAL" if tipo_raw == "PESAJE GENERAL" else "PRODUCTO_TERMINADO"

        # Producto
        prod_sel = self._combo_producto.get()
        producto_id = None
        if prod_sel and prod_sel != "-- Seleccione --":
            codigo_sel = prod_sel.split(" — ")[0]
            for p in self._productos_cache:
                if p["codigo"] == codigo_sel:
                    producto_id = p["id"]
                    break

        # Conductor -- solo se usa el conductor_id si sigue coincidiendo con
        # la cédula tipeada (si el operador la editó después de buscar, el
        # match queda obsoleto y se cae a texto libre en vez de linkear al
        # conductor equivocado).
        cedula_conductor = self._entry_cedula.get().strip()
        conductor_id = None
        if (self._conductor_seleccionado and
                self._conductor_seleccionado["documento"].upper().replace(" ", "") ==
                cedula_conductor.upper().replace(" ", "")):
            conductor_id = self._conductor_seleccionado["id"]

        resultado = api_client.registrar_entrada(
            peso_bruto=float(peso),
            vehiculo_id=vehiculo["id"],
            tipo_pesaje=tipo_key,
            producto_id=producto_id,
            empresa_transportista=self._entry_transportista.get().strip(),
            empresa_cliente_proveedor=self._entry_empresa_cp.get().strip(),
            conductor_id=conductor_id,
            cedula_conductor_libre=cedula_conductor,
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
        self._conductor_seleccionado = None
        self._lbl_conductor_info.configure(text="")
        self._entry_transportista.delete(0, "end")
        self._entry_empresa_cp.delete(0, "end")
        self._lbl_resumen_tipo.configure(text="Tipo: —")
        self._lbl_resumen_prod.configure(text="Producto: —")
        self._lbl_resumen_veh.configure(text="Vehículo: —")
