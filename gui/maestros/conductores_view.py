# gui/maestros/conductores_view.py — CRUD Conductores
import customtkinter as ctk
from tkinter import messagebox, ttk
from client.api_client import api_client, ApiError
from config import UI
from gui.async_utils import cargar_en_hilo

_DEBOUNCE_MS = 300


class ConductoresView(ctk.CTkFrame):
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
        ctk.CTkLabel(header, text="👤 CONDUCTORES", font=ctk.CTkFont(size=15, weight="bold"), text_color=UI["color_accent"]).pack(side="left")
        ctk.CTkButton(header, text="+ Nuevo", command=self._nuevo, height=32, width=90, fg_color=UI["color_accent"], hover_color=UI["color_accent_hover"]).pack(side="right")

        self._entry_buscar = ctk.CTkEntry(left, placeholder_text="🔍 Buscar por nombre o documento...", height=35)
        self._entry_buscar.grid(row=1, column=0, sticky="ew", padx=15, pady=(0,5))
        self._entry_buscar.bind("<KeyRelease>", lambda e: self._on_tecla_buscar())

        style = ttk.Style()
        style.configure("Cond.Treeview",
            background=UI["color_card"],
            foreground=UI["color_text"],
            fieldbackground=UI["color_card"],
            rowheight=26,
            font=("Helvetica",11))
        style.configure("Cond.Treeview.Heading",
            background=UI["color_bg"],
            foreground=UI["color_text"],
            font=("Helvetica",10,"bold"))
        style.map("Cond.Treeview",
            background=[("selected","#E0F2FE")],
            foreground=[("selected","#1E3A8A")])

        self._tree = ttk.Treeview(left, columns=("nombre","documento","tipo","telefono","estado"), show="headings", style="Cond.Treeview")
        for col, titulo, ancho in [("nombre","NOMBRE",200),("documento","DOCUMENTO",120),("tipo","TIPO",90),("telefono","TELÉFONO",110),("estado","ESTADO",70)]:
            self._tree.heading(col, text=titulo)
            self._tree.column(col, width=ancho)
        self._tree.grid(row=2, column=0, sticky="nsew", padx=(10,0), pady=(0,5))
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

        ctk.CTkLabel(right, text="📝 Datos del Conductor", font=ctk.CTkFont(size=14, weight="bold"), text_color=UI["color_text"]).pack(padx=18, pady=(15,10), anchor="w")
        ctk.CTkFrame(right, height=1, fg_color=UI["color_border"]).pack(fill="x", padx=15, pady=(0,15))

        self._f_nombre = self._campo(right, "Nombre completo *")
        self._f_doc    = self._campo(right, "Número de documento *")

        ctk.CTkLabel(right, text="Tipo de documento", font=ctk.CTkFont(size=11), text_color=UI["color_muted"], anchor="w").pack(fill="x", padx=18, pady=(0,2))
        self._f_tipo = ctk.CTkComboBox(right, values=["cedula","licencia","pasaporte"], height=35)
        self._f_tipo.pack(fill="x", padx=18, pady=(0,10))
        self._f_tipo.set("cedula")

        self._f_tel = self._campo(right, "Teléfono")

        btn = ctk.CTkFrame(right, fg_color="transparent")
        btn.pack(fill="x", padx=18, pady=10)
        ctk.CTkButton(btn, text="💾 Guardar", command=self._guardar, height=40, fg_color=UI["color_success"], hover_color=UI["color_success_hover"], font=ctk.CTkFont(size=13,weight="bold")).pack(fill="x", pady=(0,5))
        self._btn_desact = ctk.CTkButton(btn, text="🚫 Desactivar", command=self._desactivar, height=36, fg_color=UI["color_danger"], hover_color=UI["color_danger_hover"], state="disabled")
        self._btn_desact.pack(fill="x", pady=(0,5))
        ctk.CTkButton(btn, text="✕ Limpiar", command=self._limpiar, height=36, fg_color="transparent", border_color=UI["color_border"], border_width=1, text_color=UI["color_muted"], hover_color=UI["color_bg"]).pack(fill="x")

    def _campo(self, parent, etiqueta):
        ctk.CTkLabel(parent, text=etiqueta, font=ctk.CTkFont(size=11), text_color=UI["color_muted"], anchor="w").pack(fill="x", padx=18, pady=(0,2))
        entry = ctk.CTkEntry(parent, height=35, font=ctk.CTkFont(size=12))
        entry.pack(fill="x", padx=18, pady=(0,10))
        return entry

    def _cargar_datos(self):
        cargar_en_hilo(
            self, lambda: api_client.listar_maestro("conductores"),
            on_exito=self._poblar_tabla,
            on_error=lambda e: messagebox.showerror("Error de conexión", str(e)),
        )

    def _poblar_tabla(self, conductores):
        for item in self._tree.get_children(): self._tree.delete(item)
        for c in conductores:
            self._tree.insert("", "end", iid=str(c["id"]), values=(c["nombre"], c["documento"], c["tipo_documento"], c["telefono"] or "—", "Activo" if c["activo"] else "Inactivo"))

    def _on_tecla_buscar(self):
        if self._debounce_id:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(_DEBOUNCE_MS, self._filtrar)

    def _filtrar(self):
        termino = self._entry_buscar.get().strip()
        cargar_en_hilo(
            self, lambda: api_client.listar_maestro("conductores", search=termino or None),
            on_exito=self._poblar_tabla,
            on_error=lambda e: messagebox.showerror("Error de conexión", str(e)),
        )

    def _on_select(self, event):
        sel = self._tree.selection()
        if not sel: return
        cid = int(sel[0])
        try:
            c = api_client.obtener_maestro("conductores", cid)
        except ApiError as e:
            messagebox.showerror("Error de conexión", str(e))
            return
        self._seleccionado_id = cid
        for e, v in [(self._f_nombre, c["nombre"]),(self._f_doc, c["documento"]),(self._f_tel, c["telefono"] or "")]:
            e.delete(0,"end"); e.insert(0,v)
        self._f_tipo.set(c["tipo_documento"])
        self._btn_desact.configure(state="normal")

    def _guardar(self):
        nombre = self._f_nombre.get().strip()
        doc = self._f_doc.get().strip()
        if not nombre or not doc:
            messagebox.showerror("Error", "Nombre y documento son obligatorios")
            return
        datos = {"nombre": nombre, "documento": doc, "tipo_documento": self._f_tipo.get(), "telefono": self._f_tel.get().strip()}
        if self._seleccionado_id:
            resultado = api_client.actualizar_maestro("conductores", self._seleccionado_id, datos)
            mensaje_ok = "Conductor actualizado"
        else:
            resultado = api_client.crear_maestro("conductores", datos)
            mensaje_ok = "Conductor creado"
        if resultado["exito"]:
            messagebox.showinfo("✅", mensaje_ok)
        else:
            messagebox.showerror("Error", resultado["mensaje"])
            return
        self._limpiar(); self._cargar_datos()

    def _desactivar(self):
        if not self._seleccionado_id: return
        if not messagebox.askyesno("Confirmar", "¿Desactivar este conductor?"): return
        resultado = api_client.desactivar_maestro("conductores", self._seleccionado_id, activo=False)
        if resultado["exito"]:
            messagebox.showinfo("✅", "Conductor desactivado")
        else:
            messagebox.showerror("Error", resultado["mensaje"])
        self._limpiar(); self._cargar_datos()

    def _nuevo(self): self._limpiar()

    def _limpiar(self):
        self._seleccionado_id = None
        for e in [self._f_nombre, self._f_doc, self._f_tel]: e.delete(0,"end")
        self._f_tipo.set("cedula")
        self._btn_desact.configure(state="disabled")
        sel = self._tree.selection()
        if sel: self._tree.selection_remove(sel)
