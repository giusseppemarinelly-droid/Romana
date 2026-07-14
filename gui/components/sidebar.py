# ============================================================
# gui/components/sidebar.py — Menú lateral de navegación
# ============================================================

import customtkinter as ctk
from client.api_client import api_client
from config import UI


class Sidebar(ctk.CTkFrame):
    """
    Panel lateral izquierdo con los botones de navegación.
    Los botones visibles dependen del nivel del usuario logueado.
    """

    MENU_ITEMS = [
        # --- Sección pesaje (Romana) ---
        ("separator", "PESAJE", None),
        ("Entrada",          "pesaje_entrada",    "pesaje_entrada",  "↓"),
        ("Salida / Capturar","pesaje_salida",     "pesaje_salida",   "↑"),
        ("Completar Pesaje", "completar_pesaje",  "pesaje_completar","✔"),
        ("Kardex",           "kardex",            "reportes_ver",    "≡"),
        ("Corte",            "corte",             "corte_pesadas",   "✂"),

        # --- Sección Centro de Costos ---
        ("separator", "CENTRO DE COSTOS", None),
        ("Aprobaciones",     "centro_costos",     "centro_costos",   "📋"),

        # --- Sección maestros ---
        ("separator", "MAESTROS", None),
        ("Vehículos",   "vehiculos",   "maestros_ver", "🚛"),
        ("Conductores", "conductores", "maestros_ver", "👤"),
        ("Proveedores", "proveedores", "maestros_ver", "🏭"),
        ("Productos",   "productos",   "maestros_ver", "📦"),
        ("Destinos",    "destinos",    "maestros_ver", "📍"),

        # --- Sección administración ---
        ("separator", "ADMIN", None),
        ("Usuarios",    "usuarios",      "admin_usuarios",     "👥"),
        ("Config",      "configuracion", "admin_configuracion", "⚙"),
    ]

    def __init__(self, parent, callback_navegar, callback_logout):
        super().__init__(
            parent,
            width=230,
            corner_radius=0,
            fg_color=UI["color_sidebar"]
        )
        self.grid_propagate(False)
        self.callback_navegar = callback_navegar
        self.callback_logout = callback_logout
        self._botones = {}
        self._activo = None

        # 3 filas: logo fija, menú expandible, footer fijo
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(0, weight=1)

        self._construir()

    def _construir(self):
        usuario = api_client.usuario

        # ─── LOGO (fila 0) ────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew")

        # Franja de color en el logo (consistente con el sidebar oscuro)
        brand_frame = ctk.CTkFrame(top, fg_color="#1e293b", corner_radius=0)
        brand_frame.pack(fill="x")

        ctk.CTkLabel(
            brand_frame,
            text="⚖  ROMANA",
            font=ctk.CTkFont(family=UI["fuente"], size=20, weight="bold"),
            text_color="#FFFFFF"
        ).pack(pady=(16, 2))

        ctk.CTkLabel(
            brand_frame,
            text="Sistema de Control de Pesaje",
            font=ctk.CTkFont(family=UI["fuente"], size=10),
            text_color="#bfdbfe"   # azul muy claro
        ).pack(pady=(0, 14))

        # ─── MENÚ SCROLLABLE (fila 1) ─────────────────────────
        scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=UI["color_sidebar_hover"],
            scrollbar_button_hover_color=UI["color_accent"]
        )
        scroll.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        scroll.grid_columnconfigure(0, weight=1)

        # Dashboard (siempre visible)
        btn_dash = self._crear_boton(scroll, "🏠  Dashboard", "dashboard")
        btn_dash.pack(fill="x", padx=10, pady=(12, 4))
        self._botones["dashboard"] = btn_dash

        # Items del menú
        for item in self.MENU_ITEMS:
            tipo = item[0]

            if tipo == "separator":
                seccion = item[1]
                # Etiqueta de sección — color azul claro legible
                ctk.CTkLabel(
                    scroll,
                    text=f"  {seccion}",
                    font=ctk.CTkFont(family=UI["fuente"], size=9, weight="bold"),
                    text_color=UI["color_sidebar_section"],
                    anchor="w"
                ).pack(fill="x", padx=10, pady=(14, 2))

                ctk.CTkFrame(
                    scroll, height=1,
                    fg_color=UI["color_sidebar_hover"]
                ).pack(fill="x", padx=10, pady=(0, 4))

            else:
                texto, destino, permiso, icono = item

                if permiso and not api_client.tiene_permiso(permiso):
                    continue

                btn = self._crear_boton(scroll, f"{icono}  {texto}", destino)
                btn.pack(fill="x", padx=10, pady=1)
                self._botones[destino] = btn

        # ─── FOOTER FIJO (fila 2) ─────────────────────────────
        footer = ctk.CTkFrame(
            self,
            fg_color=UI["color_sidebar_bottom"],
            corner_radius=0
        )
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)

        # Línea separadora
        ctk.CTkFrame(footer, height=1, fg_color="#0f2744").grid(
            row=0, column=0, sticky="ew")

        # Info del usuario
        if usuario:
            nivel_info = {
                1: ("▲", "Administrador",    "#fbbf24"),
                2: ("●", "Supervisor",        "#60a5fa"),
                3: ("◆", "Operador Romana",   "#34d399"),
                4: ("⬡", "Centro de Costos",  "#f97316"),
            }
            simbolo, rol, color_rol = nivel_info.get(
                usuario["nivel"], ("●", "Usuario", "#94a3b8"))

            usuario_row = ctk.CTkFrame(footer, fg_color="transparent")
            usuario_row.grid(row=1, column=0, sticky="ew", padx=14, pady=(10, 6))
            usuario_row.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(
                usuario_row,
                text=simbolo,
                font=ctk.CTkFont(size=18),
                text_color=color_rol,
                width=28
            ).grid(row=0, column=0, rowspan=2)

            nombre_corto = usuario["nombre_completo"][:24]
            ctk.CTkLabel(
                usuario_row,
                text=nombre_corto,
                font=ctk.CTkFont(family=UI["fuente"], size=12, weight="bold"),
                text_color="#e2e8f0",
                anchor="w"
            ).grid(row=0, column=1, sticky="w", padx=(8, 0))

            ctk.CTkLabel(
                usuario_row,
                text=rol,
                font=ctk.CTkFont(family=UI["fuente"], size=10),
                text_color=color_rol,
                anchor="w"
            ).grid(row=1, column=1, sticky="w", padx=(8, 0))

        # Botón Cerrar Sesión
        btn_logout = ctk.CTkButton(
            footer,
            text="  Cerrar Sesión",
            command=self.callback_logout,
            fg_color="transparent",
            hover_color="#7f1d1d",
            text_color="#fca5a5",
            border_color="#7f1d1d",
            border_width=1,
            height=36,
            corner_radius=8,
            font=ctk.CTkFont(family=UI["fuente"], size=12),
            anchor="w"
        )
        btn_logout.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))

    def _crear_boton(self, parent, texto, destino):
        """Crea un botón del menú con estilo consistente."""
        return ctk.CTkButton(
            parent,
            text=texto,
            command=lambda d=destino: self.callback_navegar(d),
            fg_color="transparent",
            hover_color=UI["color_sidebar_hover"],
            text_color=UI["color_sidebar_text"],
            anchor="w",
            height=38,
            corner_radius=8,
            font=ctk.CTkFont(family=UI["fuente"], size=13)
        )

    def marcar_activo(self, destino: str):
        """Resalta el botón de la pantalla activa."""
        if self._activo and self._activo in self._botones:
            self._botones[self._activo].configure(
                fg_color="transparent",
                text_color=UI["color_sidebar_text"]
            )

        if destino in self._botones:
            self._botones[destino].configure(
                fg_color=UI["color_sidebar_active"],
                text_color="#FFFFFF"
            )

        self._activo = destino
