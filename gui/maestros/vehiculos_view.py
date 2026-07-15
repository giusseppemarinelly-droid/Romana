# ============================================================
# gui/maestros/vehiculos_view.py — CRUD de Vehículos
# ============================================================
# Patrón reutilizable para todos los maestros:
# Lista con búsqueda + Formulario de alta/edición/baja

import customtkinter as ctk
from tkinter import messagebox, ttk
from client.api_client import api_client, ApiError
from config import UI
from gui.async_utils import cargar_en_hilo

_DEBOUNCE_MS = 300  # espera tras la última tecla antes de buscar en el servidor


class VehiculosView(ctk.CTkFrame):
    """Pantalla CRUD de vehículos."""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._seleccionado_id = None
        self._debounce_id = None
        self._construir()
        self._cargar_datos()

    def _construir(self):
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ---- Panel izquierdo: lista ----
        left = ctk.CTkFrame(
            self,
            fg_color=UI["color_card"],
            border_color=UI["color_border"],
            border_width=1,
            corner_radius=12
        )
        left.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=20)
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(left, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))

        ctk.CTkLabel(
            header, text="🚛 VEHÍCULOS",
            font=ctk.CTkFont(family=UI["fuente"], size=15, weight="bold"),
            text_color=UI["color_accent"]
        ).pack(side="left")

        ctk.CTkButton(
            header, text="+ Nuevo",
            command=self._nuevo,
            height=32, width=90,
            font=ctk.CTkFont(family=UI["fuente"], size=12),
            fg_color=UI["color_accent"], hover_color=UI["color_accent_hover"]
        ).pack(side="right")

        # Búsqueda
        self._entry_buscar = ctk.CTkEntry(
            left, placeholder_text="🔍 Buscar por placa o descripción...",
            height=35, font=ctk.CTkFont(family=UI["fuente"], size=12)
        )
        self._entry_buscar.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 5))
        self._entry_buscar.bind("<KeyRelease>", lambda e: self._on_tecla_buscar())

        # Tabla
        style = ttk.Style()
        style.configure("Veh.Treeview",
            background=UI["color_card"],
            foreground=UI["color_text"],
            fieldbackground=UI["color_card"],
            rowheight=26,
            font=("Segoe UI", 11))
        style.configure("Veh.Treeview.Heading",
            background=UI["color_bg"],
            foreground=UI["color_text"],
            font=("Segoe UI", 10, "bold"))
        style.map("Veh.Treeview",
            background=[("selected", "#E0F2FE")],
            foreground=[("selected", "#1E3A8A")])

        self._tree = ttk.Treeview(
            left,
            columns=("placa", "descripcion", "tara", "tipo", "estado"),
            show="headings", style="Veh.Treeview"
        )
        for col, titulo, ancho in [
            ("placa",       "PLACA",       100),
            ("descripcion", "DESCRIPCIÓN", 200),
            ("tara",        "TARA (KG)",    90),
            ("tipo",        "TIPO",         90),
            ("estado",      "ESTADO",       70),
        ]:
            self._tree.heading(col, text=titulo)
            self._tree.column(col, width=ancho)

        self._tree.grid(row=2, column=0, sticky="nsew", padx=(10, 0), pady=(0, 5))
        scroll = ttk.Scrollbar(left, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=2, column=1, sticky="ns")
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        # ---- Panel derecho: formulario ----
        right = ctk.CTkFrame(
            self,
            fg_color=UI["color_card"],
            border_color=UI["color_border"],
            border_width=1,
            corner_radius=12
        )
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=20)

        ctk.CTkLabel(
            right, text="📝 Datos del Vehículo",
            font=ctk.CTkFont(family=UI["fuente"], size=14, weight="bold"),
            text_color=UI["color_text"]
        ).pack(padx=18, pady=(15, 10), anchor="w")

        ctk.CTkFrame(right, height=1, fg_color=UI["color_border"]).pack(
            fill="x", padx=15, pady=(0, 15))

        # Campos del formulario
        self._f_placa = self._campo(right, "Placa *")
        self._f_desc  = self._campo(right, "Descripción")
        self._f_tara  = self._campo(right, "Tara registrada (KG)")
        self._f_tipo  = self._combo_campo(
            right, "Tipo",
            ["camion", "tractocamion", "volqueta", "cisterna", "otro"]
        )

        # Proveedor -- el combo arranca con un solo valor y se completa
        # cuando llega la lista real (_cargar_proveedores), en vez de
        # bloquear la construcción de la pantalla esperando al backend.
        ctk.CTkLabel(right, text="Proveedor", font=ctk.CTkFont(family=UI["fuente"], size=11),
                     text_color=UI["color_muted"], anchor="w").pack(fill="x", padx=18, pady=(0, 2))
        self._proveedores_lista = []

        self._f_proveedor = ctk.CTkComboBox(
            right, values=["-- Sin proveedor --"], height=35, font=ctk.CTkFont(family=UI["fuente"], size=12))
        self._f_proveedor.pack(fill="x", padx=18, pady=(0, 12))
        self._f_proveedor.set("-- Sin proveedor --")
        self._cargar_proveedores()

        # Botones
        btn_frame = ctk.CTkFrame(right, fg_color="transparent")
        btn_frame.pack(fill="x", padx=18, pady=10)

        self._btn_guardar = ctk.CTkButton(
            btn_frame, text="💾 Guardar",
            command=self._guardar, height=40,
            fg_color=UI["color_success"], hover_color=UI["color_success_hover"],
            font=ctk.CTkFont(family=UI["fuente"], size=13, weight="bold")
        )
        self._btn_guardar.pack(fill="x", pady=(0, 5))

        if api_client.tiene_permiso("maestros_eliminar"):
            self._btn_desactivar = ctk.CTkButton(
                btn_frame, text="🚫 Desactivar",
                command=self._desactivar, height=36,
                fg_color=UI["color_danger"], hover_color=UI["color_danger_hover"],
                font=ctk.CTkFont(family=UI["fuente"], size=12),
                state="disabled"
            )
            self._btn_desactivar.pack(fill="x", pady=(0, 5))

        ctk.CTkButton(
            btn_frame, text="✕ Limpiar",
            command=self._limpiar, height=36,
            font=ctk.CTkFont(family=UI["fuente"], size=12),
            fg_color="transparent", border_color=UI["color_border"],
            border_width=1, text_color=UI["color_muted"], hover_color=UI["color_bg"]
        ).pack(fill="x")

    def _campo(self, parent, etiqueta):
        """Crea un campo de entrada estándar."""
        ctk.CTkLabel(parent, text=etiqueta, font=ctk.CTkFont(family=UI["fuente"], size=11),
                     text_color=UI["color_muted"], anchor="w").pack(fill="x", padx=18, pady=(0, 2))
        entry = ctk.CTkEntry(parent, height=35, font=ctk.CTkFont(family=UI["fuente"], size=12))
        entry.pack(fill="x", padx=18, pady=(0, 10))
        return entry

    def _combo_campo(self, parent, etiqueta, valores):
        """Crea un combo estándar."""
        ctk.CTkLabel(parent, text=etiqueta, font=ctk.CTkFont(family=UI["fuente"], size=11),
                     text_color=UI["color_muted"], anchor="w").pack(fill="x", padx=18, pady=(0, 2))
        combo = ctk.CTkComboBox(parent, values=valores, height=35, font=ctk.CTkFont(family=UI["fuente"], size=12))
        combo.pack(fill="x", padx=18, pady=(0, 10))
        combo.set(valores[0])
        return combo

    def _cargar_proveedores(self):
        cargar_en_hilo(
            self, lambda: api_client.listar_maestro("proveedores"),
            on_exito=self._on_proveedores_cargados,
            on_error=lambda e: messagebox.showerror("Error de conexión", str(e)),
        )

    def _on_proveedores_cargados(self, provs):
        self._proveedores_lista = provs
        prov_nombres = ["-- Sin proveedor --"] + [f"{p['codigo']} — {p['nombre']}" for p in provs]
        self._f_proveedor.configure(values=prov_nombres)

    def _cargar_datos(self):
        """Carga los vehículos en la tabla (búsqueda vacía = todos los activos)."""
        cargar_en_hilo(
            self, lambda: api_client.listar_maestro("vehiculos"),
            on_exito=self._poblar_tabla,
            on_error=lambda e: messagebox.showerror("Error de conexión", str(e)),
        )

    def _poblar_tabla(self, vehiculos):
        for item in self._tree.get_children():
            self._tree.delete(item)
        for v in vehiculos:
            self._tree.insert("", "end", iid=str(v["id"]), values=(
                v["placa"],
                v["descripcion"] or "—",
                f"{float(v['tara_registrada'] or 0):,.0f}",
                v["tipo"] or "—",
                "Activo" if v["activo"] else "Inactivo"
            ))

    def _on_tecla_buscar(self):
        """Espera a que el operador deje de escribir antes de golpear al servidor
        (evita una búsqueda por cada tecla — ver _DEBOUNCE_MS)."""
        if self._debounce_id:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(_DEBOUNCE_MS, self._filtrar)

    def _filtrar(self):
        """Búsqueda indexada en el servidor (ILIKE sobre placa/descripción)."""
        termino = self._entry_buscar.get().strip()
        cargar_en_hilo(
            self, lambda: api_client.listar_maestro("vehiculos", search=termino or None),
            on_exito=self._poblar_tabla,
            on_error=lambda e: messagebox.showerror("Error de conexión", str(e)),
        )

    def _on_select(self, event):
        """Al seleccionar un vehículo en la tabla, carga sus datos en el formulario."""
        sel = self._tree.selection()
        if not sel:
            return
        vid = int(sel[0])
        try:
            v = api_client.obtener_maestro("vehiculos", vid)
        except ApiError as e:
            messagebox.showerror("Error de conexión", str(e))
            return

        self._seleccionado_id = vid
        # Llenar formulario
        self._f_placa.delete(0, "end")
        self._f_placa.insert(0, v["placa"])
        self._f_desc.delete(0, "end")
        self._f_desc.insert(0, v["descripcion"] or "")
        self._f_tara.delete(0, "end")
        self._f_tara.insert(0, str(float(v["tara_registrada"] or 0)))
        self._f_tipo.set(v["tipo"] or "camion")

        # Proveedor
        if v["proveedor_id"]:
            for p in self._proveedores_lista:
                if p["id"] == v["proveedor_id"]:
                    self._f_proveedor.set(f"{p['codigo']} — {p['nombre']}")
                    break
        else:
            self._f_proveedor.set("-- Sin proveedor --")

        if hasattr(self, "_btn_desactivar"):
            self._btn_desactivar.configure(state="normal")

    def _guardar(self):
        """Guarda (crea o actualiza) el vehículo."""
        placa = self._f_placa.get().strip().upper()
        if not placa:
            messagebox.showerror("Error", "La placa es obligatoria")
            return

        desc  = self._f_desc.get().strip()
        tipo  = self._f_tipo.get()

        try:
            tara = float(self._f_tara.get().replace(",", ".") or "0")
        except ValueError:
            messagebox.showerror("Error", "La tara debe ser un número")
            return

        # Obtener proveedor_id
        prov_val = self._f_proveedor.get()
        prov_id = None
        for p in self._proveedores_lista:
            if f"{p['codigo']} — {p['nombre']}" == prov_val:
                prov_id = p["id"]
                break

        datos = {"placa": placa, "descripcion": desc, "tara_registrada": tara,
                 "tipo": tipo, "proveedor_id": prov_id}

        if self._seleccionado_id:
            resultado = api_client.actualizar_maestro("vehiculos", self._seleccionado_id, datos)
            mensaje_ok = f"Vehículo {placa} actualizado"
        else:
            resultado = api_client.crear_maestro("vehiculos", datos)
            mensaje_ok = f"Vehículo {placa} creado"

        if resultado["exito"]:
            messagebox.showinfo("✅ Éxito", mensaje_ok)
        else:
            messagebox.showerror("Error", resultado["mensaje"])
            return

        self._limpiar()
        self._cargar_datos()

    def _desactivar(self):
        if not self._seleccionado_id:
            return
        if not messagebox.askyesno("Confirmar",
                "¿Desactivar este vehículo?\nNo podrá usarse en nuevas pesadas."):
            return
        resultado = api_client.desactivar_maestro("vehiculos", self._seleccionado_id, activo=False)
        if resultado["exito"]:
            messagebox.showinfo("✅", "Vehículo desactivado")
        else:
            messagebox.showerror("Error", resultado["mensaje"])
        self._limpiar()
        self._cargar_datos()

    def _nuevo(self):
        self._limpiar()

    def _limpiar(self):
        self._seleccionado_id = None
        for entry in [self._f_placa, self._f_desc, self._f_tara]:
            entry.delete(0, "end")
        self._f_tipo.set("camion")
        self._f_proveedor.set("-- Sin proveedor --")
        if hasattr(self, "_btn_desactivar"):
            self._btn_desactivar.configure(state="disabled")
        sel = self._tree.selection()
        if sel:
            self._tree.selection_remove(sel)
