# ============================================================
# gui/admin/usuarios_view.py — Gestión de Usuarios
# ============================================================

import customtkinter as ctk
from tkinter import messagebox, ttk
from datetime import datetime
from client.api_client import api_client, ApiError
from config import UI
from gui.async_utils import cargar_en_hilo


def _fecha_hora(iso_str):
    if not iso_str:
        return "Nunca"
    return datetime.fromisoformat(iso_str).strftime("%d/%m/%Y %H:%M")


class UsuariosView(ctk.CTkFrame):
    """
    Pantalla de gestión de usuarios (solo Administradores).
    Permite crear, editar contraseñas y activar/desactivar usuarios.
    """

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._seleccionado = None
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
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(left, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))

        ctk.CTkLabel(
            header, text="👥 GESTIÓN DE USUARIOS",
            font=ctk.CTkFont(family=UI["fuente"], size=15, weight="bold"),
            text_color=UI["color_accent"]
        ).pack(side="left")

        ctk.CTkButton(
            header, text="+ Nuevo Usuario",
            command=self._nuevo,
            height=32, font=ctk.CTkFont(family=UI["fuente"], size=12), fg_color=UI["color_accent"], hover_color=UI["color_accent_hover"]
        ).pack(side="right")

        # Tabla de usuarios
        style = ttk.Style()
        style.configure("Usr.Treeview",
            background=UI["color_card"],
            foreground=UI["color_text"],
            fieldbackground=UI["color_card"],
            rowheight=30,
            font=("Segoe UI", 12))
        style.configure("Usr.Treeview.Heading",
            background=UI["color_bg"],
            foreground=UI["color_text"],
            font=("Segoe UI", 10, "bold"))
        style.map("Usr.Treeview",
            background=[("selected", "#E0F2FE")],
            foreground=[("selected", "#1E3A8A")])

        self._tree = ttk.Treeview(
            left,
            columns=("username", "nombre", "nivel", "estado", "ultimo_login"),
            show="headings", style="Usr.Treeview"
        )
        for col, titulo, ancho in [
            ("username",    "USUARIO",       110),
            ("nombre",      "NOMBRE COMPLETO",200),
            ("nivel",       "NIVEL",          130),
            ("estado",      "ESTADO",          80),
            ("ultimo_login","ÚLTIMO ACCESO",  150),
        ]:
            self._tree.heading(col, text=titulo)
            self._tree.column(col, width=ancho)

        self._tree.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=(5, 10))
        scroll = ttk.Scrollbar(left, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=1, column=1, sticky="ns")
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
            right, text="📝 Datos del Usuario",
            font=ctk.CTkFont(family=UI["fuente"], size=14, weight="bold"),
            text_color=UI["color_text"]
        ).pack(padx=18, pady=(15, 10), anchor="w")

        ctk.CTkFrame(right, height=1, fg_color=UI["color_border"]).pack(
            fill="x", padx=15, pady=(0, 15))

        # Username
        ctk.CTkLabel(right, text="Nombre de usuario *", font=ctk.CTkFont(family=UI["fuente"], size=11),
                     text_color=UI["color_muted"], anchor="w").pack(fill="x", padx=18, pady=(0, 2))
        self._f_username = ctk.CTkEntry(right, height=35, font=ctk.CTkFont(family=UI["fuente"], size=12))
        self._f_username.pack(fill="x", padx=18, pady=(0, 10))

        # Nombre completo
        ctk.CTkLabel(right, text="Nombre completo *", font=ctk.CTkFont(family=UI["fuente"], size=11),
                     text_color=UI["color_muted"], anchor="w").pack(fill="x", padx=18, pady=(0, 2))
        self._f_nombre = ctk.CTkEntry(right, height=35, font=ctk.CTkFont(family=UI["fuente"], size=12))
        self._f_nombre.pack(fill="x", padx=18, pady=(0, 10))

        # Nivel
        ctk.CTkLabel(right, text="Nivel de acceso", font=ctk.CTkFont(family=UI["fuente"], size=11),
                     text_color=UI["color_muted"], anchor="w").pack(fill="x", padx=18, pady=(0, 2))
        self._f_nivel = ctk.CTkComboBox(
            right,
            values=["1 — Administrador", "2 — Supervisor", "3 — Operador"],
            height=35, font=ctk.CTkFont(family=UI["fuente"], size=12)
        )
        self._f_nivel.pack(fill="x", padx=18, pady=(0, 15))
        self._f_nivel.set("3 — Operador")

        # Separador para contraseña
        ctk.CTkFrame(right, height=1, fg_color=UI["color_border"]).pack(
            fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(right, text="🔐 Contraseña",
                     font=ctk.CTkFont(family=UI["fuente"], size=12, weight="bold"),
                     text_color=UI["color_text"]).pack(fill="x", padx=18)

        ctk.CTkLabel(right, text="Nueva contraseña *", font=ctk.CTkFont(family=UI["fuente"], size=11),
                     text_color=UI["color_muted"], anchor="w").pack(fill="x", padx=18, pady=(5, 2))
        self._f_pass = ctk.CTkEntry(right, show="●", height=35, font=ctk.CTkFont(family=UI["fuente"], size=12))
        self._f_pass.pack(fill="x", padx=18, pady=(0, 8))

        ctk.CTkLabel(right, text="Confirmar contraseña *", font=ctk.CTkFont(family=UI["fuente"], size=11),
                     text_color=UI["color_muted"], anchor="w").pack(fill="x", padx=18, pady=(0, 2))
        self._f_pass2 = ctk.CTkEntry(right, show="●", height=35, font=ctk.CTkFont(family=UI["fuente"], size=12))
        self._f_pass2.pack(fill="x", padx=18, pady=(0, 15))

        # Botones
        btn_frame = ctk.CTkFrame(right, fg_color="transparent")
        btn_frame.pack(fill="x", padx=18, pady=5)

        ctk.CTkButton(
            btn_frame, text="💾 Guardar",
            command=self._guardar,
            height=40, font=ctk.CTkFont(family=UI["fuente"], size=13, weight="bold"),
            fg_color=UI["color_success"], hover_color=UI["color_success_hover"]
        ).pack(fill="x", pady=(0, 5))

        self._btn_activar = ctk.CTkButton(
            btn_frame, text="✅ Activar / 🚫 Desactivar",
            command=self._toggle_activo,
            height=36, font=ctk.CTkFont(family=UI["fuente"], size=12),
            fg_color=UI["color_warning"], hover_color=UI["color_accent_hover"],
            state="disabled"
        )
        self._btn_activar.pack(fill="x", pady=(0, 5))

        ctk.CTkButton(
            btn_frame, text="✕ Limpiar",
            command=self._limpiar,
            height=36, font=ctk.CTkFont(family=UI["fuente"], size=12), fg_color="transparent",
            border_color=UI["color_border"], border_width=1,
            text_color=UI["color_muted"], hover_color=UI["color_bg"]
        ).pack(fill="x")

    def _cargar_datos(self):
        cargar_en_hilo(
            self, api_client.listar_usuarios,
            on_exito=self._poblar_tabla,
            on_error=lambda e: messagebox.showerror("Error de conexión", str(e)),
        )

    def _poblar_tabla(self, usuarios):
        for item in self._tree.get_children():
            self._tree.delete(item)

        nivel_nombre = {1: "👑 Administrador", 2: "🔧 Supervisor", 3: "🔑 Operador", 4: "📋 Centro de Costos"}
        for u in usuarios:
            self._tree.insert("", "end", iid=str(u["id"]), values=(
                u["username"],
                u["nombre_completo"],
                nivel_nombre.get(u["nivel"], "—"),
                "Activo" if u["activo"] else "Inactivo",
                _fecha_hora(u.get("last_login"))
            ))

    def _on_select(self, event):
        sel = self._tree.selection()
        if not sel:
            return
        uid = int(sel[0])

        try:
            usuarios = api_client.listar_usuarios()
        except ApiError as e:
            messagebox.showerror("Error de conexión", str(e))
            return
        usuario = next((u for u in usuarios if u["id"] == uid), None)
        if not usuario:
            return

        self._seleccionado = usuario
        self._f_username.delete(0, "end")
        self._f_username.insert(0, usuario["username"])
        self._f_nombre.delete(0, "end")
        self._f_nombre.insert(0, usuario["nombre_completo"])

        nivel_opts = {1: "1 — Administrador", 2: "2 — Supervisor", 3: "3 — Operador"}
        self._f_nivel.set(nivel_opts.get(usuario["nivel"], "3 — Operador"))

        estado_txt = "🚫 Desactivar" if usuario["activo"] else "✅ Activar"
        self._btn_activar.configure(text=estado_txt, state="normal")

    def _guardar(self):
        username = self._f_username.get().strip().lower()
        nombre = self._f_nombre.get().strip()
        pass1 = self._f_pass.get()
        pass2 = self._f_pass2.get()
        nivel_txt = self._f_nivel.get()
        nivel = int(nivel_txt[0]) if nivel_txt else 3

        if not username or not nombre:
            messagebox.showerror("Error", "Usuario y nombre son obligatorios")
            return

        if self._seleccionado:
            # Edición: solo cambiar contraseña si se ingresó
            if pass1 or pass2:
                if pass1 != pass2:
                    messagebox.showerror("Error", "Las contraseñas no coinciden")
                    return
                if len(pass1) < 4:
                    messagebox.showerror("Error", "La contraseña debe tener al menos 4 caracteres")
                    return
                resultado = api_client.cambiar_password(self._seleccionado["id"], pass1)
                if resultado["exito"]:
                    messagebox.showinfo("✅", "Contraseña actualizada")
                else:
                    messagebox.showerror("Error", resultado["mensaje"])
        else:
            # Nuevo usuario
            if not pass1:
                messagebox.showerror("Error", "Ingrese una contraseña")
                return
            if pass1 != pass2:
                messagebox.showerror("Error", "Las contraseñas no coinciden")
                return
            if len(pass1) < 4:
                messagebox.showerror("Error", "La contraseña debe tener al menos 4 caracteres")
                return

            resultado = api_client.crear_usuario(username, pass1, nombre, nivel)
            if resultado["exito"]:
                messagebox.showinfo("✅", resultado["data"]["mensaje"])
            else:
                messagebox.showerror("Error", resultado["mensaje"])
                return

        self._limpiar()
        self._cargar_datos()

    def _toggle_activo(self):
        if not self._seleccionado:
            return
        # No puede desactivarse a sí mismo
        actual = api_client.usuario
        if actual and actual["id"] == self._seleccionado["id"]:
            messagebox.showerror("Error", "No puedes desactivar tu propia cuenta")
            return

        nuevo_estado = not self._seleccionado["activo"]
        accion = "activar" if nuevo_estado else "desactivar"

        if messagebox.askyesno("Confirmar", f"¿{accion.capitalize()} al usuario {self._seleccionado['username']}?"):
            resultado = api_client.activar_desactivar_usuario(self._seleccionado["id"], nuevo_estado)
            if resultado["exito"]:
                messagebox.showinfo("✅", resultado["data"]["mensaje"])
            else:
                messagebox.showerror("Error", resultado["mensaje"])
            self._limpiar()
            self._cargar_datos()

    def _nuevo(self):
        self._limpiar()

    def _limpiar(self):
        self._seleccionado = None
        for e in [self._f_username, self._f_nombre, self._f_pass, self._f_pass2]:
            e.delete(0, "end")
        self._f_nivel.set("3 — Operador")
        self._btn_activar.configure(state="disabled", text="✅ Activar / 🚫 Desactivar")
        sel = self._tree.selection()
        if sel:
            self._tree.selection_remove(sel)
