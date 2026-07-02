# ============================================================
# gui/login_view.py — Pantalla de inicio de sesión
# ============================================================

import customtkinter as ctk
from client.api_client import api_client
from config import EMPRESA, UI


class LoginView(ctk.CTkFrame):
    """
    Pantalla de login con diseño corporativo de dos paneles.
    Panel izquierdo: Branding azul corporativo.
    Panel derecho: Formulario de acceso limpio.
    """

    def __init__(self, parent, callback_login):
        super().__init__(parent, fg_color=UI["color_bg"], corner_radius=0)
        self.callback_login = callback_login
        self._construir()

    def _construir(self):
        self.grid_columnconfigure(0, weight=5)    # Panel izquierdo (branding)
        self.grid_columnconfigure(1, weight=7)    # Panel derecho (formulario)
        self.grid_rowconfigure(0, weight=1)

        self._construir_panel_izquierdo()
        self._construir_panel_derecho()

    # ----------------------------------------------------------
    def _construir_panel_izquierdo(self):
        """Panel izquierdo azul corporativo con branding."""
        panel = ctk.CTkFrame(
            self,
            fg_color=UI["color_sidebar"],   # Oscuro original
            corner_radius=0
        )
        panel.grid(row=0, column=0, sticky="nsew")
        panel.grid_rowconfigure(0, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        # Contenido centrado
        centro = ctk.CTkFrame(panel, fg_color="transparent")
        centro.grid(row=0, column=0)

        # Ícono grande
        ctk.CTkLabel(
            centro,
            text="⚖",
            font=ctk.CTkFont(size=80),
            text_color="#FFFFFF"
        ).pack(pady=(0, 16))

        # Nombre del sistema
        ctk.CTkLabel(
            centro,
            text="ROMANA",
            font=ctk.CTkFont(family=UI["fuente"], size=40, weight="bold"),
            text_color="#FFFFFF"
        ).pack()

        # Línea decorativa
        ctk.CTkFrame(
            centro, height=3, width=70,
            fg_color="#334155"           # Sutil sobre fondo oscuro
        ).pack(pady=(10, 14))

        ctk.CTkLabel(
            centro,
            text="Sistema de Control\nde Pesaje de Camiones",
            font=ctk.CTkFont(family=UI["fuente"], size=15),
            text_color="#94a3b8",        # Gris claro — legible sobre oscuro
            justify="center"
        ).pack()

        # Características del sistema (bullets)
        features_frame = ctk.CTkFrame(
            centro,
            fg_color="#1e293b",          # Oscuro sobre oscuro — buen contraste
            corner_radius=10
        )
        features_frame.pack(pady=(30, 0), padx=20, fill="x")

        features = [
            "✓  Control de entradas y salidas",
            "✓  Gestión de pesadas y tickets",
            "✓  Reportes en PDF y Excel",
            "✓  Control de acceso por usuario",
        ]
        for f in features:
            ctk.CTkLabel(
                features_frame,
                text=f,
                font=ctk.CTkFont(family=UI["fuente"], size=12),
                text_color="#94a3b8",    # Gris claro sobre oscuro
                anchor="w"
            ).pack(anchor="w", padx=16, pady=3)

        ctk.CTkFrame(features_frame, height=4, fg_color="transparent").pack()

        # Pie de empresa (anclado al fondo del panel)
        empresa_frame = ctk.CTkFrame(
            panel,
            fg_color="#070e1c",          # Más oscuro que el fondo para contraste
            corner_radius=0
        )
        empresa_frame.grid(row=0, column=0, sticky="sew")
        empresa_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            empresa_frame,
            text=EMPRESA["nombre"],
            font=ctk.CTkFont(family=UI["fuente"], size=13, weight="bold"),
            text_color="#e2e8f0"         # Blanco suave
        ).grid(row=0, column=0, padx=20, pady=(12, 2))

        ctk.CTkLabel(
            empresa_frame,
            text=f"RIF: {EMPRESA['rif']}  |  {EMPRESA['telefono']}",
            font=ctk.CTkFont(family=UI["fuente"], size=11),
            text_color="#475569"         # Gris visible
        ).grid(row=1, column=0, padx=20, pady=(0, 12))

    # ----------------------------------------------------------
    def _construir_panel_derecho(self):
        """Panel derecho con el formulario de acceso."""
        panel = ctk.CTkFrame(self, fg_color=UI["color_bg"], corner_radius=0)
        panel.grid(row=0, column=1, sticky="nsew")
        panel.grid_rowconfigure(0, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        # Card centrada verticalmente
        card = ctk.CTkFrame(
            panel,
            fg_color=UI["color_card"],
            border_color=UI["color_border"],
            border_width=1,
            corner_radius=16
        )
        card.grid(row=0, column=0, padx=50, pady=50, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)

        # Franja azul superior en la card
        stripe = ctk.CTkFrame(card, fg_color=UI["color_accent"],
                               height=6, corner_radius=0)
        stripe.grid(row=0, column=0, sticky="ew")
        # Fix corners del top
        ctk.CTkFrame(card, fg_color=UI["color_accent"],
                     height=6, width=16).place(x=0, y=0)

        # Encabezado
        ctk.CTkLabel(
            card,
            text="Acceso al Sistema",
            font=ctk.CTkFont(family=UI["fuente"], size=26, weight="bold"),
            text_color=UI["color_text"]
        ).grid(row=1, column=0, padx=40, pady=(30, 4), sticky="w")

        ctk.CTkLabel(
            card,
            text="Ingrese sus credenciales para continuar",
            font=ctk.CTkFont(family=UI["fuente"], size=13),
            text_color=UI["color_muted"]
        ).grid(row=2, column=0, padx=40, pady=(0, 24), sticky="w")

        # Separador
        ctk.CTkFrame(card, height=1, fg_color=UI["color_border"]).grid(
            row=3, column=0, sticky="ew", padx=30, pady=(0, 24))

        # --- Campo Usuario ---
        ctk.CTkLabel(
            card,
            text="USUARIO",
            font=ctk.CTkFont(family=UI["fuente"], size=10, weight="bold"),
            text_color=UI["color_muted"]
        ).grid(row=4, column=0, padx=40, sticky="w")

        self._entry_usuario = ctk.CTkEntry(
            card,
            placeholder_text="Nombre de usuario",
            height=46,
            font=ctk.CTkFont(family=UI["fuente"], size=14),
            corner_radius=8,
            border_color=UI["color_border"],
            border_width=2,
            fg_color="#f8fafc"
        )
        self._entry_usuario.grid(row=5, column=0, padx=40, pady=(6, 18), sticky="ew")
        self._entry_usuario.focus()

        # --- Campo Contraseña ---
        ctk.CTkLabel(
            card,
            text="CONTRASEÑA",
            font=ctk.CTkFont(family=UI["fuente"], size=10, weight="bold"),
            text_color=UI["color_muted"]
        ).grid(row=6, column=0, padx=40, sticky="w")

        self._entry_password = ctk.CTkEntry(
            card,
            placeholder_text="Contraseña",
            show="●",
            height=46,
            font=ctk.CTkFont(family=UI["fuente"], size=14),
            corner_radius=8,
            border_color=UI["color_border"],
            border_width=2,
            fg_color="#f8fafc"
        )
        self._entry_password.grid(row=7, column=0, padx=40, pady=(6, 8), sticky="ew")

        # Mensaje de error
        self._lbl_error = ctk.CTkLabel(
            card,
            text="",
            font=ctk.CTkFont(family=UI["fuente"], size=12),
            text_color=UI["color_danger"]
        )
        self._lbl_error.grid(row=8, column=0, padx=40, pady=(0, 8))

        # Botón principal
        btn = ctk.CTkButton(
            card,
            text="INGRESAR AL SISTEMA",
            command=self._intentar_login,
            height=50,
            font=ctk.CTkFont(family=UI["fuente"], size=14, weight="bold"),
            corner_radius=8,
            fg_color=UI["color_accent"],
            hover_color=UI["color_accent_hover"]
        )
        btn.grid(row=9, column=0, padx=40, pady=(10, 28), sticky="ew")

        # Versión
        ctk.CTkLabel(
            card,
            text="v1.0  —  Sistema de Romana para Camiones",
            font=ctk.CTkFont(family=UI["fuente"], size=10),
            text_color=UI["color_muted"]
        ).grid(row=10, column=0, padx=40, pady=(0, 28))

        # Atajos de teclado
        self._entry_usuario.bind("<Return>", lambda e: self._entry_password.focus())
        self._entry_password.bind("<Return>", lambda e: self._intentar_login())

    # ----------------------------------------------------------
    def _intentar_login(self):
        """Valida las credenciales y navega si son correctas."""
        usuario = self._entry_usuario.get().strip()
        password = self._entry_password.get()

        self._lbl_error.configure(text="")

        if not usuario or not password:
            self._lbl_error.configure(text="  Complete usuario y contraseña")
            return

        resultado = api_client.login(usuario, password)

        if resultado["exito"]:
            self.callback_login()
        else:
            self._lbl_error.configure(text=f"  {resultado['mensaje']}")
            self._entry_password.delete(0, "end")
            self._entry_password.focus()
