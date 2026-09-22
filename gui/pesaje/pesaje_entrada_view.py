# ============================================================
# gui/pesaje/pesaje_entrada_view.py — Registro de Entrada
# ============================================================

import customtkinter as ctk
from tkinter import messagebox
from config import UI
from client.api_client import api_client, ApiError
from hardware.display_manager import leer_peso_actual, es_peso_estable
from gui.async_utils import cargar_en_hilo
from gui.components.combo_buscable import ComboBuscable
from gui.components.dialogo_alta_rapida import DialogoAltaRapida
from gui.components.dialogo_seleccion import DialogoSeleccion
from gui.components.ui_kit import (
    Card, PesoDisplay, boton_primario, boton_secundario,
    titulo_h1, titulo_h2, etiqueta_campo, texto_ayuda, ocultar_scrollbar,
)


TIPO_PESAJE_OPCIONES = ["PESAJE GENERAL", "PRODUCTO TERMINADO"]

# Estilo compartido de campos de entrada — fondo levemente distinto de
# la tarjeta (color_input_bg) y borde de 2px, para que se noten como
# "editables" en vez del recuadro plano que traía CTk por defecto. Radio
# de control del sistema de diseño (docs/design-system.md sección 4).
_INPUT_STYLE = dict(
    fg_color=UI["color_input_bg"],
    border_color=UI["color_border"],
    border_width=2,
    corner_radius=UI["radio_control"],
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
        self._transportista_seleccionada = None
        self._proveedor_seleccionado = None
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
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 12))
        header.grid_columnconfigure(0, weight=1)

        titulo_h1(header, "Registro de Entrada").grid(row=0, column=0, sticky="w")
        texto_ayuda(
            header, "Complete los datos y capture el peso de la báscula."
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        # ── Cuerpo con dos columnas ──────────────────────────
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 20))
        # minsize en la columna del panel derecho (resumen + botón registrar)
        # para que nunca quede apachurrado contra el borde de la ventana en
        # monitores de menor resolución que el diseño asumido -- sin esto, el
        # peso relativo (3:2) igual deja el panel casi invisible cuando el
        # ancho total disponible es chico.
        body.grid_columnconfigure(0, weight=3, minsize=420)
        body.grid_columnconfigure(1, weight=2, minsize=260)
        body.grid_rowconfigure(0, weight=1)

        self._construir_formulario(body)
        self._construir_panel_peso(body)

    # ----------------------------------------------------------
    def _construir_formulario(self, parent):
        """Panel izquierdo — campos del formulario."""
        card_outer = Card(parent)
        card_outer.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=10)
        card_outer.grid_columnconfigure(0, weight=1)
        card_outer.grid_rowconfigure(0, weight=1)

        # El formulario completo (tipo, producto, vehículo, conductor,
        # transportista, empresas) puede superar en altura a la ventana
        # en monitores de menor resolución -- sin scroll, los últimos
        # campos quedaban tapados por el borde de la ventana sin forma
        # de alcanzarlos (ver fix de minsize en _construir() para el
        # mismo síntoma en el ancho).
        card = ctk.CTkScrollableFrame(card_outer, fg_color="transparent",
                                       label_text="")
        card.grid(row=0, column=0, sticky="nsew")
        ocultar_scrollbar(card)
        card.grid_columnconfigure((0, 1), weight=1)

        row = 0

        # ── Tipo de pesaje ────────────────────────────────────
        self._seccion(card, "TIPO DE PESAJE", row); row += 1

        # Producto Terminado por defecto -- es el tipo de pesaje más usado
        # en la práctica, pedido explícitamente por el usuario.
        self._tipo_var = ctk.StringVar(value="PRODUCTO TERMINADO")
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
            text_color=UI["color_brand"],
            fg_color=UI["color_brand_tint"], corner_radius=UI["radio_control"],
            width=50, height=40, anchor="center"
        )
        self._lbl_cod_prod.grid(row=0, column=0, padx=(0, 8))

        self._combo_producto = ComboBuscable(
            prod_frame,
            command=self._on_producto_changed,
            height=40,
            font=ctk.CTkFont(family=UI["fuente"], size=13),
            placeholder_text="Escriba para buscar el producto...",
        )
        self._combo_producto.grid(row=0, column=1, sticky="ew")
        row += 1

        # ── Vehículo ──────────────────────────────────────────
        self._seccion(card, "VEHÍCULO", row); row += 1

        veh_frame = ctk.CTkFrame(card, fg_color="transparent")
        veh_frame.grid(row=row, column=0, columnspan=2, sticky="ew",
                        padx=18, pady=(4, 10))
        veh_frame.grid_columnconfigure(0, weight=1)

        # Entry simple, no ComboBuscable -- pedido explícito del usuario
        # (2026-09-17): separar "escribo la placa y confirmo con
        # Buscar" de "no sé la placa, quiero ver la lista completa"
        # (Buscar con el campo vacío abre DialogoSeleccion). El filtro
        # en vivo mientras se escribía se sentía ruidoso.
        self._entry_vehiculo = ctk.CTkEntry(
            veh_frame, placeholder_text="Ingrese la placa...",
            height=40, font=ctk.CTkFont(family=UI["fuente"], size=13),
            **_INPUT_STYLE,
        )
        self._entry_vehiculo.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._entry_vehiculo.bind("<Return>", lambda e: self._buscar_vehiculo())

        boton_secundario(
            veh_frame, "🔍 Buscar", command=self._buscar_vehiculo, width=96,
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

        boton_secundario(
            cond_frame, "🔍 Buscar", command=self._buscar_conductor, width=96,
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
        # Mismo patrón que Vehículo/Conductor: se busca por código contra
        # el maestro de Empresas Transportistas y, si existe, autocompleta
        # el nombre y guarda empresa_transportista_id (mejor para kardex/
        # reportes); si no existe, sigue funcionando como texto libre.
        self._seccion(card, "EMPRESA TRANSPORTISTA", row); row += 1

        transp_frame = ctk.CTkFrame(card, fg_color="transparent")
        transp_frame.grid(row=row, column=0, columnspan=2, sticky="ew",
                           padx=18, pady=(4, 4))
        transp_frame.grid_columnconfigure(0, weight=1)

        self._entry_cod_transportista = ctk.CTkEntry(
            transp_frame, placeholder_text="Código de la empresa transportista",
            height=40, font=ctk.CTkFont(family=UI["fuente"], size=13),
            **_INPUT_STYLE,
        )
        self._entry_cod_transportista.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._entry_cod_transportista.bind("<Return>", lambda e: self._buscar_transportista())

        boton_secundario(
            transp_frame, "🔍 Buscar", command=self._buscar_transportista, width=96,
        ).grid(row=0, column=1)
        row += 1

        self._entry_transportista = ctk.CTkEntry(
            card, placeholder_text="Nombre de la empresa transportista",
            height=40, font=ctk.CTkFont(family=UI["fuente"], size=13),
            **_INPUT_STYLE,
        )
        self._entry_transportista.grid(row=row, column=0, columnspan=2,
                                        sticky="ew", padx=18, pady=(0, 4))
        row += 1

        self._lbl_transportista_info = ctk.CTkLabel(
            card, text="",
            font=ctk.CTkFont(family=UI["fuente"], size=11),
            text_color=UI["color_muted"]
        )
        self._lbl_transportista_info.grid(row=row, column=0, columnspan=2,
                                           padx=18, pady=(0, 6), sticky="w")
        row += 1

        # ── Empresa Cliente / Proveedor ───────────────────────
        # Igual patrón, contra el maestro de Proveedores ya existente --
        # antes este campo era texto libre y proveedor_id nunca se
        # enviaba al backend (se perdía siempre, aunque el servicio ya
        # lo acepta).
        self._seccion(card, "EMPRESA (CLIENTE O PROVEEDOR)", row); row += 1

        prov_frame = ctk.CTkFrame(card, fg_color="transparent")
        prov_frame.grid(row=row, column=0, columnspan=2, sticky="ew",
                         padx=18, pady=(4, 4))
        prov_frame.grid_columnconfigure(0, weight=1)

        self._entry_cod_proveedor = ctk.CTkEntry(
            prov_frame, placeholder_text="Código del cliente o proveedor",
            height=40, font=ctk.CTkFont(family=UI["fuente"], size=13),
            **_INPUT_STYLE,
        )
        self._entry_cod_proveedor.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._entry_cod_proveedor.bind("<Return>", lambda e: self._buscar_proveedor())

        boton_secundario(
            prov_frame, "🔍 Buscar", command=self._buscar_proveedor, width=96,
        ).grid(row=0, column=1)
        row += 1

        self._entry_empresa_cp = ctk.CTkEntry(
            card, placeholder_text="Nombre de la empresa cliente o proveedor",
            height=40, font=ctk.CTkFont(family=UI["fuente"], size=13),
            **_INPUT_STYLE,
        )
        self._entry_empresa_cp.grid(row=row, column=0, columnspan=2,
                                     sticky="ew", padx=18, pady=(0, 4))
        row += 1

        self._lbl_proveedor_info = ctk.CTkLabel(
            card, text="",
            font=ctk.CTkFont(family=UI["fuente"], size=11),
            text_color=UI["color_muted"]
        )
        self._lbl_proveedor_info.grid(row=row, column=0, columnspan=2,
                                       padx=18, pady=(0, 18), sticky="w")
        row += 1

        # ── Procedencia (de dónde viene el producto) ──────────
        self._seccion(card, "PROCEDENCIA (opcional)", row); row += 1

        self._entry_procedencia = ctk.CTkEntry(
            card, placeholder_text="De dónde viene el producto (ej. nombre de la finca/planta de origen)",
            height=40, font=ctk.CTkFont(family=UI["fuente"], size=13),
            **_INPUT_STYLE,
        )
        self._entry_procedencia.grid(row=row, column=0, columnspan=2,
                                      sticky="ew", padx=18, pady=(4, 18))
        row += 1

        # Cargar productos por defecto (PRODUCTO_TERMINADO, ver _tipo_var)
        self._cargar_productos("PRODUCTO_TERMINADO")

    # ----------------------------------------------------------
    def _construir_panel_peso(self, parent):
        """Panel derecho — báscula y botón registrar."""
        panel = ctk.CTkFrame(parent, fg_color="transparent")
        panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=10)
        panel.grid_columnconfigure(0, weight=1)

        # ── Peso en vivo ──────────────────────────────────────
        bascula_card = Card(panel)
        bascula_card.grid(row=0, column=0, sticky="ew")
        bascula_card.grid_columnconfigure(0, weight=1)

        etiqueta_campo(bascula_card, "Peso báscula").grid(
            row=0, column=0, padx=16, pady=(18, 4)
        )

        self._peso_display = PesoDisplay(bascula_card)
        self._peso_display.grid(row=1, column=0, padx=16, pady=(0, 4), sticky="ew")

        boton_secundario(
            bascula_card, "↻  Actualizar peso", command=self._actualizar_peso,
        ).grid(row=2, column=0, padx=16, pady=(8, 8), sticky="ew")

        # ── Peso manual (si la báscula no responde) ───────────
        self._peso_manual_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            bascula_card, text="⌨  Ingresar peso manualmente",
            variable=self._peso_manual_var, command=self._toggle_peso_manual,
            font=ctk.CTkFont(family=UI["fuente"], size=11),
            fg_color=UI["color_accent"], hover_color=UI["color_accent_hover"],
            border_color=UI["color_border"],
        ).grid(row=3, column=0, padx=16, pady=(0, 4))

        self._entry_peso_manual = ctk.CTkEntry(
            bascula_card, placeholder_text="Peso en KG",
            height=36, font=ctk.CTkFont(family=UI["fuente"], size=14),
            **_INPUT_STYLE,
        )
        self._entry_peso_manual.grid(row=4, column=0, padx=16, pady=(0, 16), sticky="ew")
        self._entry_peso_manual.grid_remove()  # oculto hasta marcar el checkbox

        # ── Resumen ───────────────────────────────────────────
        resumen_card = Card(panel)
        resumen_card.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        resumen_card.grid_columnconfigure(0, weight=1)

        titulo_h2(resumen_card, "Resumen").grid(
            row=0, column=0, padx=16, pady=(14, 8), sticky="w"
        )

        self._lbl_resumen_tipo = ctk.CTkLabel(
            resumen_card, text="Tipo: —",
            font=ctk.CTkFont(family=UI["fuente"], size=UI["fuente_body"]),
            text_color=UI["color_text"]
        )
        self._lbl_resumen_tipo.grid(row=1, column=0, padx=16, pady=2, sticky="w")

        self._lbl_resumen_prod = ctk.CTkLabel(
            resumen_card, text="Producto: —",
            font=ctk.CTkFont(family=UI["fuente"], size=UI["fuente_body"]),
            text_color=UI["color_text"]
        )
        self._lbl_resumen_prod.grid(row=2, column=0, padx=16, pady=2, sticky="w")

        self._lbl_resumen_veh = ctk.CTkLabel(
            resumen_card, text="Vehículo: —",
            font=ctk.CTkFont(family=UI["fuente"], size=UI["fuente_body"]),
            text_color=UI["color_text"]
        )
        self._lbl_resumen_veh.grid(row=3, column=0, padx=16, pady=(2, 14), sticky="w")

        # ── Botón registrar ───────────────────────────────────
        boton_primario(
            panel, "↓  REGISTRAR ENTRADA", command=self._registrar, height=56,
        ).grid(row=2, column=0, sticky="ew", pady=(12, 0))

    # ----------------------------------------------------------
    def _seccion(self, parent, texto, row):
        """Etiqueta de sección dentro del formulario."""
        etiqueta_campo(parent, texto).grid(
            row=row, column=0, columnspan=2, sticky="w", padx=18, pady=(12, 0)
        )

    # ----------------------------------------------------------
    def _cargar_vehiculos(self):
        cargar_en_hilo(
            self, lambda: api_client.listar_maestro("vehiculos"),
            on_exito=self._on_vehiculos_cargados,
            on_error=lambda e: messagebox.showerror("Error de conexión", str(e)),
        )

    def _on_vehiculos_cargados(self, vehiculos):
        self._vehiculos_map = {v["placa"]: v for v in vehiculos}

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
        self._combo_producto.configure(values=nombres)
        self._combo_producto.set("")
        self._lbl_cod_prod.configure(text="—")

    # ----------------------------------------------------------
    def _on_tipo_changed(self):
        tipo_raw = self._tipo_var.get()
        tipo_key = "GENERAL" if tipo_raw == "PESAJE GENERAL" else "PRODUCTO_TERMINADO"
        self._cargar_productos(tipo_key)
        self._lbl_resumen_tipo.configure(text=f"Tipo: {tipo_raw}")

    # ----------------------------------------------------------
    def _on_producto_changed(self, seleccion):
        if not seleccion:
            self._lbl_cod_prod.configure(text="—")
            self._lbl_resumen_prod.configure(text="Producto: —")
            return
        # Extraer código del texto "002 — Chatarra"
        codigo = seleccion.split(" — ")[0]
        self._lbl_cod_prod.configure(text=codigo)
        nombre = seleccion.split(" — ")[1] if " — " in seleccion else seleccion
        self._lbl_resumen_prod.configure(text=f"Producto: {nombre}")

    # ----------------------------------------------------------
    def _seleccionar_vehiculo(self, v):
        """Deja un vehículo (dict) como seleccionado y refleja los datos
        en pantalla -- común a "encontrado buscando", "elegido del
        DialogoSeleccion" y "recién creado en DialogoAltaRapida"."""
        self._entry_vehiculo.delete(0, "end")
        self._entry_vehiculo.insert(0, v["placa"])
        self._vehiculo_seleccionado = v
        tara = f"{float(v['tara_registrada']):,.0f}" if v["tara_registrada"] else "N/A"
        self._lbl_vehiculo_info.configure(
            text=f"{v['descripcion'] or ''}  |  Tara registrada: {tara} KG"
        )
        self._lbl_resumen_veh.configure(text=f"Vehículo: {v['placa']}")
        self._autocompletar_proveedor_de_vehiculo(v)

    # ----------------------------------------------------------
    def _buscar_vehiculo(self):
        placa = self._entry_vehiculo.get().strip().upper()

        if not placa:
            # Campo vacío -- en vez de solo avisar, mostrar directamente
            # el listado completo con su propio filtro (pedido explícito
            # del usuario: separar "escribo y confirmo" de "no sé,
            # quiero ver todo").
            if not self._vehiculos_map:
                messagebox.showinfo("Sin datos", "Todavía no terminó de cargar el catálogo de vehículos.")
                return
            items = [
                (f"{v['placa']} — {v['descripcion'] or 'sin descripción'}", v)
                for v in sorted(self._vehiculos_map.values(), key=lambda v: v["placa"])
            ]
            DialogoSeleccion(
                self, titulo="Seleccionar Vehículo",
                items=items, on_elegido=self._seleccionar_vehiculo,
            )
            return

        v = self._vehiculos_map.get(placa)
        if v:
            self._seleccionar_vehiculo(v)
        else:
            if messagebox.askyesno("Vehículo no registrado",
                f"La placa '{placa}' no está en el catálogo.\n\n"
                "¿Desea registrarla ahora? (alta rápida, sin salir de esta pantalla)"):
                DialogoAltaRapida(
                    self, titulo="Nuevo Vehículo", recurso="vehiculos",
                    campos=[("placa", "Placa", True), ("descripcion", "Descripción", False)],
                    valores_iniciales={"placa": placa},
                    on_creado=self._on_vehiculo_creado,
                )

    def _on_vehiculo_creado(self, vehiculo):
        """Callback de DialogoAltaRapida -- deja el vehículo recién creado
        seleccionado, exactamente como si lo hubiera encontrado buscando."""
        self._vehiculos_map[vehiculo["placa"]] = vehiculo
        self._seleccionar_vehiculo(vehiculo)

    # ----------------------------------------------------------
    def _autocompletar_proveedor_de_vehiculo(self, vehiculo):
        """
        Si el vehículo tiene un proveedor asociado (Vehiculo.proveedor_id,
        cargado desde Maestros → Vehículos) lo autocompleta acá -- la
        mayoría de los vehículos siempre cargan/entregan para el mismo
        proveedor, así se ahorra buscarlo a mano cada vez que se repite
        la placa. No pisa nada que el operador ya haya escrito o
        buscado antes de elegir el vehículo (a mano o de una pesada
        anterior en la misma sesión de formulario).
        """
        proveedor_id = vehiculo.get("proveedor_id")
        if not proveedor_id or self._entry_cod_proveedor.get().strip():
            return
        cargar_en_hilo(
            self, lambda: api_client.obtener_maestro("proveedores", proveedor_id),
            on_exito=self._on_proveedor_de_vehiculo_cargado,
            on_error=lambda e: None,  # no molestar con un error acá -- el operador puede seguir a mano
        )

    def _on_proveedor_de_vehiculo_cargado(self, proveedor):
        if self._entry_cod_proveedor.get().strip():
            return  # el operador ya escribió/buscó algo mientras esto cargaba
        self._proveedor_seleccionado = proveedor
        self._entry_cod_proveedor.delete(0, "end")
        self._entry_cod_proveedor.insert(0, proveedor["codigo"])
        self._entry_empresa_cp.delete(0, "end")
        self._entry_empresa_cp.insert(0, proveedor["nombre"])
        self._lbl_proveedor_info.configure(
            text=f"✓ Autocompletado del vehículo  |  {proveedor.get('telefono') or 'sin teléfono'}",
            text_color=UI["color_success"]
        )

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
            # Campo vacío -- mismo criterio que Vehículo: mostrar el
            # listado completo con filtro propio, no solo un aviso.
            cargar_en_hilo(
                self, lambda: api_client.listar_maestro("conductores"),
                on_exito=self._abrir_selector_conductor,
                on_error=lambda e: messagebox.showerror("Error de conexión", str(e)),
            )
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
            self._seleccionar_conductor(c)
        else:
            self._lbl_conductor_info.configure(
                text="Conductor no registrado — se guardará solo con la cédula ingresada.",
                text_color=UI["color_muted"]
            )
            if messagebox.askyesno("Conductor no registrado",
                f"La cédula '{cedula}' no está en el catálogo.\n\n"
                "¿Desea registrarlo ahora? (alta rápida, sin salir de esta pantalla)"):
                DialogoAltaRapida(
                    self, titulo="Nuevo Conductor", recurso="conductores",
                    campos=[
                        ("documento", "Cédula / Documento", True),
                        ("nombre", "Nombre completo", True),
                        ("telefono", "Teléfono", False),
                    ],
                    valores_iniciales={
                        "documento": cedula,
                        "nombre": self._entry_nombre_conductor.get().strip(),
                    },
                    on_creado=self._seleccionar_conductor,
                )

    def _abrir_selector_conductor(self, conductores):
        if not conductores:
            messagebox.showinfo("Sin datos", "Todavía no hay conductores registrados.")
            return
        items = [
            (f"{c['documento']} — {c['nombre']}", c)
            for c in sorted(conductores, key=lambda c: c["nombre"])
        ]
        DialogoSeleccion(
            self, titulo="Seleccionar Conductor",
            items=items, on_elegido=self._seleccionar_conductor,
        )

    def _seleccionar_conductor(self, conductor):
        self._conductor_seleccionado = conductor
        self._entry_cedula.delete(0, "end")
        self._entry_cedula.insert(0, conductor["documento"])
        self._entry_nombre_conductor.delete(0, "end")
        self._entry_nombre_conductor.insert(0, conductor["nombre"])
        self._lbl_conductor_info.configure(
            text=f"✓ Conductor registrado  |  {conductor.get('telefono') or 'sin teléfono'}",
            text_color=UI["color_success"]
        )

    # ----------------------------------------------------------
    def _buscar_transportista(self):
        """Busca la empresa transportista por código (igual patrón que Conductor).

        Si existe, autocompleta el nombre y la deja linkeada por
        empresa_transportista_id. Si no existe, el operador puede seguir
        escribiendo el nombre a mano -- se guarda como texto libre
        (empresa_transportista).
        """
        codigo = self._entry_cod_transportista.get().strip()

        if not codigo:
            cargar_en_hilo(
                self, lambda: api_client.listar_maestro("empresas_transportistas"),
                on_exito=self._abrir_selector_transportista,
                on_error=lambda e: messagebox.showerror("Error de conexión", str(e)),
            )
            return

        self._transportista_seleccionada = None
        try:
            encontrados = api_client.listar_maestro("empresas_transportistas", search=codigo)
        except ApiError as e:
            messagebox.showerror("Error de conexión", str(e))
            return

        codigo_norm = codigo.upper().replace(" ", "")
        t = next(
            (x for x in encontrados
             if x["codigo"].upper().replace(" ", "") == codigo_norm),
            None
        )

        if t:
            self._seleccionar_transportista(t)
        else:
            self._lbl_transportista_info.configure(
                text="No registrada — se guardará solo con el nombre ingresado.",
                text_color=UI["color_muted"]
            )
            if messagebox.askyesno("Empresa transportista no registrada",
                f"El código '{codigo}' no está en el catálogo.\n\n"
                "¿Desea registrarla ahora? (alta rápida, sin salir de esta pantalla)"):
                DialogoAltaRapida(
                    self, titulo="Nueva Empresa Transportista", recurso="empresas_transportistas",
                    campos=[
                        ("codigo", "Código", True),
                        ("nombre", "Nombre", True),
                        ("telefono", "Teléfono", False),
                    ],
                    valores_iniciales={
                        "codigo": codigo,
                        "nombre": self._entry_transportista.get().strip(),
                    },
                    on_creado=self._seleccionar_transportista,
                )

    def _abrir_selector_transportista(self, transportistas):
        if not transportistas:
            messagebox.showinfo("Sin datos", "Todavía no hay empresas transportistas registradas.")
            return
        items = [
            (f"{t['codigo']} — {t['nombre']}", t)
            for t in sorted(transportistas, key=lambda t: t["nombre"])
        ]
        DialogoSeleccion(
            self, titulo="Seleccionar Empresa Transportista",
            items=items, on_elegido=self._seleccionar_transportista,
        )

    def _seleccionar_transportista(self, transportista):
        self._transportista_seleccionada = transportista
        self._entry_cod_transportista.delete(0, "end")
        self._entry_cod_transportista.insert(0, transportista["codigo"])
        self._entry_transportista.delete(0, "end")
        self._entry_transportista.insert(0, transportista["nombre"])
        self._lbl_transportista_info.configure(
            text=f"✓ Empresa registrada  |  {transportista.get('telefono') or 'sin teléfono'}",
            text_color=UI["color_success"]
        )

    # ----------------------------------------------------------
    def _buscar_proveedor(self):
        """Busca el cliente/proveedor por código contra el maestro de Proveedores
        (igual patrón que Conductor/Transportista).

        Si existe, autocompleta el nombre y lo deja linkeado por
        proveedor_id. Si no existe, sigue funcionando como texto libre
        (empresa_cliente_proveedor).
        """
        codigo = self._entry_cod_proveedor.get().strip()

        if not codigo:
            cargar_en_hilo(
                self, lambda: api_client.listar_maestro("proveedores"),
                on_exito=self._abrir_selector_proveedor,
                on_error=lambda e: messagebox.showerror("Error de conexión", str(e)),
            )
            return

        self._proveedor_seleccionado = None
        try:
            encontrados = api_client.listar_maestro("proveedores", search=codigo)
        except ApiError as e:
            messagebox.showerror("Error de conexión", str(e))
            return

        codigo_norm = codigo.upper().replace(" ", "")
        p = next(
            (x for x in encontrados
             if x["codigo"].upper().replace(" ", "") == codigo_norm),
            None
        )

        if p:
            self._seleccionar_proveedor(p)
        else:
            self._lbl_proveedor_info.configure(
                text="No registrado — se guardará solo con el nombre ingresado.",
                text_color=UI["color_muted"]
            )
            if messagebox.askyesno("Cliente/Proveedor no registrado",
                f"El código '{codigo}' no está en el catálogo.\n\n"
                "¿Desea registrarlo ahora? (alta rápida, sin salir de esta pantalla)"):
                DialogoAltaRapida(
                    self, titulo="Nuevo Cliente/Proveedor", recurso="proveedores",
                    campos=[
                        ("codigo", "Código", True),
                        ("nombre", "Nombre", True),
                        ("telefono", "Teléfono", False),
                    ],
                    valores_iniciales={
                        "codigo": codigo,
                        "nombre": self._entry_empresa_cp.get().strip(),
                    },
                    on_creado=self._seleccionar_proveedor,
                )

    def _abrir_selector_proveedor(self, proveedores):
        if not proveedores:
            messagebox.showinfo("Sin datos", "Todavía no hay clientes/proveedores registrados.")
            return
        items = [
            (f"{p['codigo']} — {p['nombre']}", p)
            for p in sorted(proveedores, key=lambda p: p["nombre"])
        ]
        DialogoSeleccion(
            self, titulo="Seleccionar Cliente/Proveedor",
            items=items, on_elegido=self._seleccionar_proveedor,
        )

    def _seleccionar_proveedor(self, proveedor):
        self._proveedor_seleccionado = proveedor
        self._entry_cod_proveedor.delete(0, "end")
        self._entry_cod_proveedor.insert(0, proveedor["codigo"])
        self._entry_empresa_cp.delete(0, "end")
        self._entry_empresa_cp.insert(0, proveedor["nombre"])
        self._lbl_proveedor_info.configure(
            text=f"✓ Proveedor registrado  |  {proveedor.get('telefono') or 'sin teléfono'}",
            text_color=UI["color_success"]
        )

    # ----------------------------------------------------------
    def _toggle_peso_manual(self):
        """Muestra/oculta el campo de peso manual según el checkbox."""
        if self._peso_manual_var.get():
            self._entry_peso_manual.grid()
            self._entry_peso_manual.focus()
        else:
            self._entry_peso_manual.grid_remove()

    def _obtener_peso(self) -> float:
        """
        Peso a usar para registrar: el tipeado a mano si está marcado el
        checkbox de peso manual, o el que lea la báscula en caso
        contrario. Pensado para cuando la báscula no responde
        (mantenimiento, corte de energía al adaptador, etc.) -- ver
        Pesada.es_manual.
        """
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
    def _actualizar_peso(self):
        """Lee el peso de la báscula y actualiza la pantalla."""
        try:
            peso = leer_peso_actual()
            self._peso_display.set_peso(peso, es_peso_estable() if peso is not None else False)
        except Exception:
            self._peso_display.set_error()

        # Auto-refrescar cada 0.5s -- antes eran 3s porque leer_peso_actual()
        # podía tardar hasta el timeout del driver (2s) si la báscula
        # callaba y congelar la ventana; ahora solo lee una variable en
        # memoria actualizada por un hilo de fondo (ver hardware/
        # display_manager.py, hallazgo C-04), así que refrescar seguido
        # es gratis y el operador ve el peso ponerse al día más rápido.
        self._after_id_peso = self.after(250, self._actualizar_peso)

    # ----------------------------------------------------------
    def _registrar(self):
        """Valida y registra la entrada del camión."""
        # Peso
        peso = self._obtener_peso()

        if peso <= 0:
            if self._peso_manual_var.get():
                messagebox.showerror("Sin peso",
                    "Ingrese un peso manual válido (mayor a 0).")
            else:
                messagebox.showerror("Sin peso",
                    "No hay un peso válido en la báscula.\n"
                    "Asegúrese de que el vehículo esté sobre la báscula y el peso esté estable.\n\n"
                    "Si la báscula no responde, puede tildar \"Ingresar peso manualmente\".")
            return

        # Hallazgo I-03: antes se podía registrar con el peso todavía
        # oscilando -- el cartel de "Estabilizando..." era solo cosmético,
        # no bloqueaba nada. No aplica al peso manual (no hay báscula de
        # la que leer estabilidad).
        if not self._peso_manual_var.get() and not es_peso_estable():
            messagebox.showerror("Peso inestable",
                "El peso todavía se está estabilizando.\n"
                "Espere a que el indicador diga \"PESO ESTABLE\" antes de registrar.")
            return

        # Vehículo
        placa_raw = self._entry_vehiculo.get().strip()
        if not placa_raw:
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
        if prod_sel:
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

        # Empresa Transportista y Proveedor -- mismo criterio anti-stale
        # que Conductor: solo se linkea por id si el código buscado sigue
        # coincidiendo con lo que hay en el campo (si el operador lo
        # editó después de buscar, se cae a texto libre).
        codigo_transportista = self._entry_cod_transportista.get().strip()
        empresa_transportista_id = None
        if (self._transportista_seleccionada and
                self._transportista_seleccionada["codigo"].upper().replace(" ", "") ==
                codigo_transportista.upper().replace(" ", "")):
            empresa_transportista_id = self._transportista_seleccionada["id"]

        codigo_proveedor = self._entry_cod_proveedor.get().strip()
        proveedor_id = None
        if (self._proveedor_seleccionado and
                self._proveedor_seleccionado["codigo"].upper().replace(" ", "") ==
                codigo_proveedor.upper().replace(" ", "")):
            proveedor_id = self._proveedor_seleccionado["id"]

        resultado = api_client.registrar_entrada(
            peso_bruto=float(peso),
            vehiculo_id=vehiculo["id"],
            tipo_pesaje=tipo_key,
            producto_id=producto_id,
            empresa_transportista=self._entry_transportista.get().strip(),
            empresa_transportista_id=empresa_transportista_id,
            empresa_cliente_proveedor=self._entry_empresa_cp.get().strip(),
            proveedor_id=proveedor_id,
            conductor_id=conductor_id,
            cedula_conductor_libre=cedula_conductor,
            observaciones="",
            procedencia=self._entry_procedencia.get().strip(),
            es_manual=self._peso_manual_var.get(),
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
        self._tipo_var.set("PRODUCTO TERMINADO")
        self._cargar_productos("PRODUCTO_TERMINADO")
        self._entry_vehiculo.delete(0, "end")
        self._vehiculo_seleccionado = None
        self._lbl_vehiculo_info.configure(text="")
        self._entry_cedula.delete(0, "end")
        self._entry_nombre_conductor.delete(0, "end")
        self._conductor_seleccionado = None
        self._lbl_conductor_info.configure(text="")
        self._entry_cod_transportista.delete(0, "end")
        self._entry_transportista.delete(0, "end")
        self._transportista_seleccionada = None
        self._lbl_transportista_info.configure(text="")
        self._entry_cod_proveedor.delete(0, "end")
        self._entry_empresa_cp.delete(0, "end")
        self._proveedor_seleccionado = None
        self._lbl_proveedor_info.configure(text="")
        self._entry_procedencia.delete(0, "end")
        self._peso_manual_var.set(False)
        self._entry_peso_manual.delete(0, "end")
        self._toggle_peso_manual()
        self._lbl_resumen_tipo.configure(text="Tipo: —")
        self._lbl_resumen_prod.configure(text="Producto: —")
        self._lbl_resumen_veh.configure(text="Vehículo: —")
