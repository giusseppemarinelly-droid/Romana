# ============================================================
# gui/components/header.py — Barra superior de la aplicación
# ============================================================

import customtkinter as ctk
from datetime import datetime
from client.api_client import api_client
from config import UI
from hardware.display_manager import estado_display


class Header(ctk.CTkFrame):
    """
    Barra superior corporativa que muestra:
    - Título de la pantalla actual
    - Reloj en tiempo real
    - Nombre y rol del usuario logueado
    """

    def __init__(self, parent, callback_logout=None):
        super().__init__(
            parent,
            height=58,
            corner_radius=0,
            fg_color=UI["color_card"]
        )
        self.grid_propagate(False)
        self.callback_logout = callback_logout
        self._titulo_label = None
        self._reloj_label = None

        self._construir()
        self._actualizar_reloj()

    def _construir(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Línea de acento azul a la izquierda del título (detalle corporativo)
        ctk.CTkFrame(
            self,
            width=4,
            fg_color=UI["color_accent"],
            corner_radius=2
        ).grid(row=0, column=0, sticky="ns", padx=(12, 0), pady=8)

        # Título de la pantalla
        self._titulo_label = ctk.CTkLabel(
            self,
            text="Dashboard",
            font=ctk.CTkFont(family=UI["fuente"], size=16, weight="bold"),
            text_color=UI["color_text"]
        )
        self._titulo_label.grid(row=0, column=1, padx=(10, 20), pady=15, sticky="w")

        # Estado de la báscula -- visible en TODAS las pantallas, no solo en
        # las de pesaje. Si el sistema quedó sin display o con el simulador,
        # el operador tiene que poder notarlo sin ir a buscarlo: los kilos que
        # muestra el simulador son aleatorios y por fuera son indistinguibles
        # de los reales.
        self._badge_bascula(self)

        # Reloj
        self._reloj_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(family=UI["fuente"], size=12),
            text_color=UI["color_muted"]
        )
        self._reloj_label.grid(row=0, column=3, padx=(0, 16), pady=15)

        # Separador vertical
        ctk.CTkFrame(
            self, width=1, fg_color=UI["color_border"]
        ).grid(row=0, column=4, sticky="ns", pady=12)

        # Usuario logueado con badge de rol
        usuario = api_client.usuario
        if usuario:
            nivel_info = {
                1: ("Administrador", UI["color_accent"]),
                2: ("Supervisor",    "#0891b2"),
                3: ("Operador",      UI["color_success"]),
            }
            rol_texto, rol_color = nivel_info.get(
                usuario["nivel"], ("Usuario", UI["color_muted"]))

            user_frame = ctk.CTkFrame(self, fg_color="transparent")
            user_frame.grid(row=0, column=5, padx=(16, 20), pady=8)

            # Badge de rol — usando frame pequeño en lugar de padx/pady en CTkLabel
            badge_frame = ctk.CTkFrame(
                user_frame,
                fg_color=rol_color,
                corner_radius=4
            )
            badge_frame.pack(anchor="e")

            ctk.CTkLabel(
                badge_frame,
                text=rol_texto,
                font=ctk.CTkFont(family=UI["fuente"], size=9, weight="bold"),
                text_color="#ffffff",
                fg_color="transparent"
            ).pack(padx=6, pady=1)

            ctk.CTkLabel(
                user_frame,
                text=f"  {usuario['nombre_completo']}",
                font=ctk.CTkFont(family=UI["fuente"], size=12),
                text_color=UI["color_text"]
            ).pack(anchor="e")

        # Borde inferior
        ctk.CTkFrame(
            self, height=1, fg_color=UI["color_border"]
        ).grid(row=1, column=0, columnspan=6, sticky="ew")

    def _badge_bascula(self, parent):
        """
        Indicador del origen de los pesos. Solo se dibuja cuando hay algo que
        advertir: con la báscula real conectada no ocupa lugar, porque ahí es
        el estado esperado y un badge permanente sería ruido.
        """
        estado = estado_display()
        if estado["conectado"] and not estado["es_simulador"]:
            return

        if estado["es_simulador"]:
            texto, color = "◆  SIMULADOR — pesos inventados", UI["color_danger"]
        elif estado["hay_display"]:
            texto, color = f"◆  Báscula sin señal ({estado['puerto']})", UI["color_warning"]
        else:
            texto, color = f"◆  Sin báscula ({estado['puerto']})", UI["color_warning"]

        badge = ctk.CTkFrame(parent, fg_color=color, corner_radius=4)
        badge.grid(row=0, column=2, padx=(0, 12), pady=15)
        ctk.CTkLabel(
            badge, text=texto,
            font=ctk.CTkFont(family=UI["fuente"], size=10, weight="bold"),
            text_color="#ffffff", fg_color="transparent"
        ).pack(padx=8, pady=3)

    def actualizar_titulo(self, titulo: str):
        """Actualiza el título mostrado en el header."""
        if self._titulo_label:
            # Limpiar emojis del título para display más limpio
            self._titulo_label.configure(text=titulo)

    def _actualizar_reloj(self):
        """Actualiza el reloj cada segundo."""
        if self._reloj_label:
            ahora = datetime.now().strftime("%d/%m/%Y   %H:%M:%S")
            self._reloj_label.configure(text=f"  {ahora}")
            self.after(1000, self._actualizar_reloj)
