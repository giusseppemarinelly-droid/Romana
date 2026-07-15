# gui/maestros/proveedores_view.py — CRUD Proveedores
import customtkinter as ctk
from tkinter import messagebox, ttk
from client.api_client import api_client, ApiError
from config import UI
from gui.async_utils import cargar_en_hilo

_DEBOUNCE_MS = 300


class ProveedoresView(ctk.CTkFrame):
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

        left = ctk.CTkFrame(
            self,
            fg_color=UI["color_card"],
            border_color=UI["color_border"],
            border_width=1,
            corner_radius=12
        )
        left.grid(row=0, column=0, sticky="nsew", padx=(20,10), pady=20)
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(left, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15,5))
        ctk.CTkLabel(header, text="🏭 PROVEEDORES", font=ctk.CTkFont(family=UI["fuente"], size=15,weight="bold"), text_color=UI["color_accent"]).pack(side="left")
        ctk.CTkButton(header, text="+ Nuevo", command=self._nuevo, height=32, width=90, font=ctk.CTkFont(family=UI["fuente"], size=12), fg_color=UI["color_accent"], hover_color=UI["color_accent_hover"]).pack(side="right")

        self._entry_buscar = ctk.CTkEntry(left, placeholder_text="🔍 Buscar...", height=35)
        self._entry_buscar.grid(row=1, column=0, sticky="ew", padx=15, pady=(0,5))
        self._entry_buscar.bind("<KeyRelease>", lambda e: self._on_tecla_buscar())

        style = ttk.Style()
        style.configure("Prov.Treeview",
            background=UI["color_card"],
            foreground=UI["color_text"],
            fieldbackground=UI["color_card"],
            rowheight=26,
            font=("Segoe UI",11))
        style.configure("Prov.Treeview.Heading",
            background=UI["color_bg"],
            foreground=UI["color_text"],
            font=("Segoe UI",10,"bold"))
        style.map("Prov.Treeview",
            background=[("selected","#E0F2FE")],
            foreground=[("selected","#1E3A8A")])

        self._tree = ttk.Treeview(left, columns=("codigo","nombre","rif","telefono","estado"), show="headings", style="Prov.Treeview")
        for col, titulo, ancho in [("codigo","CÓDIGO",80),("nombre","NOMBRE",220),("rif","RIF",110),("telefono","TELÉFONO",110),("estado","ESTADO",70)]:
            self._tree.heading(col, text=titulo)
            self._tree.column(col, width=ancho)
        self._tree.grid(row=2, column=0, sticky="nsew", padx=(10,0))
        scroll = ttk.Scrollbar(left, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=2, column=1, sticky="ns")
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        right = ctk.CTkFrame(
            self,
            fg_color=UI["color_card"],
            border_color=UI["color_border"],
            border_width=1,
            corner_radius=12
        )
        right.grid(row=0, column=1, sticky="nsew", padx=(10,20), pady=20)

        ctk.CTkLabel(right, text="📝 Datos del Proveedor", font=ctk.CTkFont(family=UI["fuente"], size=14,weight="bold"), text_color=UI["color_text"]).pack(padx=18, pady=(15,10), anchor="w")
        ctk.CTkFrame(right, height=1, fg_color=UI["color_border"]).pack(fill="x", padx=15, pady=(0,15))

        self._f_codigo    = self._campo(right, "Código *")
        self._f_nombre    = self._campo(right, "Nombre / Razón Social *")
        self._f_rif       = self._campo(right, "RIF / NIT / RFC")
        self._f_telefono  = self._campo(right, "Teléfono")
        self._f_email     = self._campo(right, "Email")
        self._f_direccion = self._campo(right, "Dirección")

        btn = ctk.CTkFrame(right, fg_color="transparent")
        btn.pack(fill="x", padx=18, pady=10)
        ctk.CTkButton(btn, text="💾 Guardar", command=self._guardar, height=40, font=ctk.CTkFont(family=UI["fuente"], size=13, weight="bold"), fg_color=UI["color_success"], hover_color=UI["color_success_hover"]).pack(fill="x", pady=(0,5))
        self._btn_desact = ctk.CTkButton(btn, text="🚫 Desactivar", command=self._desactivar, height=36, font=ctk.CTkFont(family=UI["fuente"], size=12), fg_color=UI["color_danger"], hover_color=UI["color_danger_hover"], state="disabled")
        self._btn_desact.pack(fill="x", pady=(0,5))
        ctk.CTkButton(btn, text="✕ Limpiar", command=self._limpiar, height=36, font=ctk.CTkFont(family=UI["fuente"], size=12), fg_color="transparent", border_color=UI["color_border"], border_width=1, text_color=UI["color_muted"], hover_color=UI["color_bg"]).pack(fill="x")

    def _campo(self, parent, etiqueta):
        ctk.CTkLabel(parent, text=etiqueta, font=ctk.CTkFont(family=UI["fuente"], size=11), text_color=UI["color_muted"], anchor="w").pack(fill="x", padx=18, pady=(0,2))
        entry = ctk.CTkEntry(parent, height=35, font=ctk.CTkFont(family=UI["fuente"], size=12))
        entry.pack(fill="x", padx=18, pady=(0,8))
        return entry

    def _cargar_datos(self):
        cargar_en_hilo(
            self, lambda: api_client.listar_maestro("proveedores"),
            on_exito=self._poblar_tabla,
            on_error=lambda e: messagebox.showerror("Error de conexión", str(e)),
        )

    def _poblar_tabla(self, items):
        for item in self._tree.get_children(): self._tree.delete(item)
        for p in items:
            self._tree.insert("", "end", iid=str(p["id"]), values=(p["codigo"], p["nombre"], p["rif"] or "—", p["telefono"] or "—", "Activo" if p["activo"] else "Inactivo"))

    def _on_tecla_buscar(self):
        if self._debounce_id:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(_DEBOUNCE_MS, self._filtrar)

    def _filtrar(self):
        termino = self._entry_buscar.get().strip()
        cargar_en_hilo(
            self, lambda: api_client.listar_maestro("proveedores", search=termino or None),
            on_exito=self._poblar_tabla,
            on_error=lambda e: messagebox.showerror("Error de conexión", str(e)),
        )

    def _on_select(self, event):
        sel = self._tree.selection()
        if not sel: return
        pid = int(sel[0])
        try:
            p = api_client.obtener_maestro("proveedores", pid)
        except ApiError as e:
            messagebox.showerror("Error de conexión", str(e))
            return
        self._seleccionado_id = pid
        pairs = [(self._f_codigo,p["codigo"]),(self._f_nombre,p["nombre"]),(self._f_rif,p["rif"] or ""),(self._f_telefono,p["telefono"] or ""),(self._f_email,p["email"] or ""),(self._f_direccion,p["direccion"] or "")]
        for e,v in pairs: e.delete(0,"end"); e.insert(0,v)
        self._btn_desact.configure(state="normal")

    def _guardar(self):
        codigo = self._f_codigo.get().strip().upper()
        nombre = self._f_nombre.get().strip()
        if not codigo or not nombre:
            messagebox.showerror("Error","Código y nombre son obligatorios"); return
        datos = {"codigo": codigo, "nombre": nombre, "rif": self._f_rif.get().strip(),
                 "telefono": self._f_telefono.get().strip(), "email": self._f_email.get().strip(),
                 "direccion": self._f_direccion.get().strip()}
        if self._seleccionado_id:
            resultado = api_client.actualizar_maestro("proveedores", self._seleccionado_id, datos)
            mensaje_ok = "Proveedor actualizado"
        else:
            resultado = api_client.crear_maestro("proveedores", datos)
            mensaje_ok = "Proveedor creado"
        if resultado["exito"]:
            messagebox.showinfo("✅", mensaje_ok)
        else:
            messagebox.showerror("Error", resultado["mensaje"])
            return
        self._limpiar(); self._cargar_datos()

    def _desactivar(self):
        if not self._seleccionado_id: return
        if not messagebox.askyesno("Confirmar","¿Desactivar este proveedor?"): return
        resultado = api_client.desactivar_maestro("proveedores", self._seleccionado_id, activo=False)
        if not resultado["exito"]:
            messagebox.showerror("Error", resultado["mensaje"])
        self._limpiar(); self._cargar_datos()

    def _nuevo(self): self._limpiar()
    def _limpiar(self):
        self._seleccionado_id = None
        for e in [self._f_codigo,self._f_nombre,self._f_rif,self._f_telefono,self._f_email,self._f_direccion]: e.delete(0,"end")
        self._btn_desact.configure(state="disabled")
