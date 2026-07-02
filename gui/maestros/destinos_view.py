# gui/maestros/destinos_view.py — CRUD Destinos
import customtkinter as ctk
from tkinter import messagebox, ttk
from database.engine import SessionLocal
from database.models import Destino
from config import UI


class DestinosView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._seleccionado_id = None
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
        ctk.CTkLabel(header, text="📍 DESTINOS", font=ctk.CTkFont(size=15,weight="bold"), text_color=UI["color_accent"]).pack(side="left")
        ctk.CTkButton(header, text="+ Nuevo", command=self._nuevo, height=32, width=90, fg_color=UI["color_accent"], hover_color=UI["color_accent_hover"]).pack(side="right")

        self._entry_buscar = ctk.CTkEntry(left, placeholder_text="🔍 Buscar...", height=35)
        self._entry_buscar.grid(row=1, column=0, sticky="ew", padx=15, pady=(0,5))
        self._entry_buscar.bind("<KeyRelease>", lambda e: self._filtrar())

        style = ttk.Style()
        style.configure("Dest.Treeview",
            background=UI["color_card"],
            foreground=UI["color_text"],
            fieldbackground=UI["color_card"],
            rowheight=26,
            font=("Helvetica",11))
        style.configure("Dest.Treeview.Heading",
            background=UI["color_bg"],
            foreground=UI["color_text"],
            font=("Helvetica",10,"bold"))
        style.map("Dest.Treeview",
            background=[("selected","#E0F2FE")],
            foreground=[("selected","#1E3A8A")])

        self._tree = ttk.Treeview(left, columns=("codigo","nombre","descripcion","estado"), show="headings", style="Dest.Treeview")
        for col, titulo, ancho in [("codigo","CÓDIGO",90),("nombre","NOMBRE",200),("descripcion","DESCRIPCIÓN",220),("estado","ESTADO",70)]:
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

        ctk.CTkLabel(right, text="📝 Datos del Destino", font=ctk.CTkFont(size=14,weight="bold"), text_color=UI["color_text"]).pack(padx=18, pady=(15,10), anchor="w")
        ctk.CTkFrame(right, height=1, fg_color=UI["color_border"]).pack(fill="x", padx=15, pady=(0,15))

        self._f_codigo = self._campo(right, "Código *")
        self._f_nombre = self._campo(right, "Nombre *")
        ctk.CTkLabel(right, text="Descripción", font=ctk.CTkFont(size=11), text_color=UI["color_muted"], anchor="w").pack(fill="x", padx=18)
        self._f_desc = ctk.CTkTextbox(right, height=80, font=ctk.CTkFont(size=12))
        self._f_desc.pack(fill="x", padx=18, pady=(2,12))

        btn = ctk.CTkFrame(right, fg_color="transparent")
        btn.pack(fill="x", padx=18, pady=10)
        ctk.CTkButton(btn, text="💾 Guardar", command=self._guardar, height=40, fg_color=UI["color_success"], hover_color=UI["color_success_hover"]).pack(fill="x", pady=(0,5))
        self._btn_desact = ctk.CTkButton(btn, text="🚫 Desactivar", command=self._desactivar, height=36, fg_color=UI["color_danger"], hover_color=UI["color_danger_hover"], state="disabled")
        self._btn_desact.pack(fill="x", pady=(0,5))
        ctk.CTkButton(btn, text="✕ Limpiar", command=self._limpiar, height=36, fg_color="transparent", border_color=UI["color_border"], border_width=1, text_color=UI["color_muted"], hover_color=UI["color_bg"]).pack(fill="x")

    def _campo(self, parent, etiqueta):
        ctk.CTkLabel(parent, text=etiqueta, font=ctk.CTkFont(size=11), text_color=UI["color_muted"], anchor="w").pack(fill="x", padx=18, pady=(0,2))
        entry = ctk.CTkEntry(parent, height=35, font=ctk.CTkFont(size=12))
        entry.pack(fill="x", padx=18, pady=(0,10))
        return entry

    def _cargar_datos(self):
        db = SessionLocal()
        try:
            self._data = db.query(Destino).order_by(Destino.nombre).all()
        finally:
            db.close()
        self._poblar_tabla(self._data)

    def _poblar_tabla(self, items):
        for item in self._tree.get_children(): self._tree.delete(item)
        for d in items:
            self._tree.insert("","end",iid=str(d.id),values=(d.codigo, d.nombre, d.descripcion or "—", "Activo" if d.activo else "Inactivo"))

    def _filtrar(self):
        t = self._entry_buscar.get().lower()
        self._poblar_tabla([d for d in self._data if t in d.nombre.lower() or t in d.codigo.lower()])

    def _on_select(self, event):
        sel = self._tree.selection()
        if not sel: return
        did = int(sel[0])
        db = SessionLocal()
        try:
            d = db.query(Destino).filter_by(id=did).first()
            if not d: return
            self._seleccionado_id = did
            self._f_codigo.delete(0,"end"); self._f_codigo.insert(0, d.codigo)
            self._f_nombre.delete(0,"end"); self._f_nombre.insert(0, d.nombre)
            self._f_desc.delete("1.0","end"); self._f_desc.insert("1.0", d.descripcion or "")
            self._btn_desact.configure(state="normal")
        finally:
            db.close()

    def _guardar(self):
        codigo = self._f_codigo.get().strip().upper()
        nombre = self._f_nombre.get().strip()
        if not codigo or not nombre:
            messagebox.showerror("Error","Código y nombre son obligatorios"); return
        db = SessionLocal()
        try:
            if self._seleccionado_id:
                d = db.query(Destino).filter_by(id=self._seleccionado_id).first()
                if d: d.codigo=codigo; d.nombre=nombre; d.descripcion=self._f_desc.get("1.0","end").strip(); db.commit(); messagebox.showinfo("✅","Destino actualizado")
            else:
                if db.query(Destino).filter_by(codigo=codigo).first():
                    messagebox.showerror("Error","Código ya existe"); return
                db.add(Destino(codigo=codigo, nombre=nombre, descripcion=self._f_desc.get("1.0","end").strip()))
                db.commit(); messagebox.showinfo("✅","Destino creado")
        except Exception as e:
            db.rollback(); messagebox.showerror("Error",str(e))
        finally:
            db.close()
        self._limpiar(); self._cargar_datos()

    def _desactivar(self):
        if not self._seleccionado_id: return
        db = SessionLocal()
        try:
            d = db.query(Destino).filter_by(id=self._seleccionado_id).first()
            if d: d.activo=False; db.commit()
        finally:
            db.close()
        self._limpiar(); self._cargar_datos()

    def _nuevo(self): self._limpiar()
    def _limpiar(self):
        self._seleccionado_id = None
        self._f_codigo.delete(0,"end"); self._f_nombre.delete(0,"end"); self._f_desc.delete("1.0","end")
        self._btn_desact.configure(state="disabled")
