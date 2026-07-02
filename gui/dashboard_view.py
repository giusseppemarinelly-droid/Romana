# ============================================================
# gui/dashboard_view.py — Pantalla principal del dashboard
# ============================================================

import customtkinter as ctk
from services.auth_service import get_usuario_actual, tiene_permiso
from services.pesaje_service import listar_pesadas_pendientes, listar_pesadas_completadas
from datetime import datetime
from config import UI


class DashboardView(ctk.CTkFrame):
    """
    Panel principal que se muestra después del login.
    Muestra:
     - Tarjetas con métricas clave (pendientes, completadas hoy)
     - Accesos rápidos a las funciones principales
     - Lista de pesadas pendientes (camiones en planta)
    """

    def __init__(self, parent, callback_navegar):
        super().__init__(parent, fg_color="transparent")
        self.callback_navegar = callback_navegar
        self._construir()

    def _construir(self):
        """Construye el dashboard."""
        usuario = get_usuario_actual()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ---- Saludo ----
        saludo_frame = ctk.CTkFrame(self, fg_color="transparent")
        saludo_frame.grid(row=0, column=0, sticky="ew", padx=25, pady=(20, 5))

        hora = datetime.now().hour
        saludo = "Buenos días" if hora < 12 else "Buenas tardes" if hora < 18 else "Buenas noches"
        nombre = usuario.nombre_completo if usuario else "Usuario"

        ctk.CTkLabel(
            saludo_frame,
            text=f"  {saludo}, {nombre}",
            font=ctk.CTkFont(family=UI["fuente"], size=24, weight="bold"),
            text_color=UI["color_text"]
        ).pack(anchor="w")

        ctk.CTkLabel(
            saludo_frame,
            text=datetime.now().strftime("  %A, %d de %B de %Y"),
            font=ctk.CTkFont(family=UI["fuente"], size=13),
            text_color=UI["color_muted"]
        ).pack(anchor="w", pady=(2, 0))

        # ---- Tarjetas de métricas ----
        metrics_frame = ctk.CTkFrame(self, fg_color="transparent")
        metrics_frame.grid(row=1, column=0, sticky="ew", padx=25, pady=15)

        # Obtener datos
        pendientes = listar_pesadas_pendientes()
        completadas = listar_pesadas_completadas(limit=500)
        hoy = datetime.now().date()
        completadas_hoy = [p for p in completadas
                           if p.fecha_salida and p.fecha_salida.date() == hoy]
        total_neto_hoy = sum(float(p.peso_neto or 0) for p in completadas_hoy)

        metricas = [
            ("🚛", "Camiones en Planta", str(len(pendientes)),       UI["color_warning"],       "pesaje_salida"),
            ("✅", "Pesadas Hoy",         str(len(completadas_hoy)), UI["color_accent"],         "kardex"),
            ("⚖️",  "Neto Hoy (KG)",      f"{total_neto_hoy:,.0f}", UI["color_success"],        "kardex"),
            ("📋", "Total Completadas",   str(len(completadas)),     UI["color_accent_hover"],   "kardex"),
        ]

        for i, (icono, titulo, valor, color, destino) in enumerate(metricas):
            card = ctk.CTkFrame(
                metrics_frame,
                fg_color=UI["color_card"],
                border_color=UI["color_border"],
                border_width=1,
                corner_radius=12
            )
            card.grid(row=0, column=i, padx=8, pady=0, sticky="ew")
            metrics_frame.grid_columnconfigure(i, weight=1)

            ctk.CTkLabel(
                card, text=icono,
                font=ctk.CTkFont(size=28)
            ).pack(anchor="w", padx=18, pady=(15, 0))

            ctk.CTkLabel(
                card, text=valor,
                font=ctk.CTkFont(size=26, weight="bold"),
                text_color=color
            ).pack(anchor="w", padx=18)

            ctk.CTkLabel(
                card, text=titulo,
                font=ctk.CTkFont(size=11),
                text_color=UI["color_muted"]
            ).pack(anchor="w", padx=18, pady=(0, 15))

        # ---- Accesos rápidos + Lista de pendientes ----
        lower_frame = ctk.CTkFrame(self, fg_color="transparent")
        lower_frame.grid(row=2, column=0, sticky="nsew", padx=25, pady=0)
        lower_frame.grid_columnconfigure(0, weight=2)
        lower_frame.grid_columnconfigure(1, weight=3)
        lower_frame.grid_rowconfigure(0, weight=1)

        # --- Accesos rápidos ---
        self._construir_accesos_rapidos(lower_frame)

        # --- Lista de pendientes ---
        self._construir_lista_pendientes(lower_frame, pendientes)

    def _construir_accesos_rapidos(self, parent):
        """Botones grandes de acceso rápido."""
        frame = ctk.CTkFrame(
            parent,
            fg_color=UI["color_card"],
            border_color=UI["color_border"],
            border_width=1,
            corner_radius=12
        )
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=10)

        ctk.CTkLabel(
            frame, text="⚡ Accesos Rápidos",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=UI["color_text"]
        ).pack(anchor="w", padx=18, pady=(15, 10))

        # Definición de accesos: (texto, destino, es_primario, permiso)
        accesos = [
            ("⬇  Registrar Entrada", "pesaje_entrada", True,  "pesaje_entrada"),
            ("⬆  Registrar Salida",  "pesaje_salida",  True,  "pesaje_salida"),
            ("≡  Ver Kardex",         "kardex",         False, "reportes_ver"),
            ("✂  Realizar Corte",    "corte",          False, "corte_pesadas"),
            ("🚛  Gestionar Vehículos","vehiculos",     False, "maestros_ver"),
        ]

        for texto, destino, primario, permiso in accesos:
            if not tiene_permiso(permiso):
                continue
            if primario:
                # Botón principal: azul sólido, sin borde
                btn = ctk.CTkButton(
                    frame,
                    text=texto,
                    command=lambda d=destino: self.callback_navegar(d),
                    height=44,
                    font=ctk.CTkFont(family=UI["fuente"], size=13, weight="bold"),
                    fg_color=UI["color_accent"],
                    hover_color=UI["color_accent_hover"],
                    text_color="#ffffff",
                    corner_radius=8,
                    anchor="w"
                )
            else:
                # Botón secundario: fondo blanco con borde azul
                btn = ctk.CTkButton(
                    frame,
                    text=texto,
                    command=lambda d=destino: self.callback_navegar(d),
                    height=44,
                    font=ctk.CTkFont(family=UI["fuente"], size=13),
                    fg_color=UI["color_card"],
                    hover_color=UI["color_bg"],
                    text_color=UI["color_text"],
                    border_color=UI["color_accent"],
                    border_width=1,
                    corner_radius=8,
                    anchor="w"
                )
            btn.pack(fill="x", padx=15, pady=3)

        ctk.CTkFrame(frame, fg_color="transparent").pack(fill="both", expand=True)

    def _construir_lista_pendientes(self, parent, pendientes):
        """Lista de camiones actualmente en planta (pesadas pendientes)."""
        frame = ctk.CTkFrame(
            parent,
            fg_color=UI["color_card"],
            border_color=UI["color_border"],
            border_width=1,
            corner_radius=12
        )
        frame.grid(row=0, column=1, sticky="nsew", pady=10)

        # Header de la lista
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(15, 5))

        ctk.CTkLabel(
            header,
            text=f"🚛 Camiones en Planta ({len(pendientes)})",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=UI["color_text"]
        ).pack(side="left")

        ctk.CTkButton(
            header,
            text="↻ Actualizar",
            width=90,
            height=28,
            font=ctk.CTkFont(size=11),
            command=self._refrescar,
            fg_color=UI["color_accent"],
            hover_color=UI["color_accent_hover"]
        ).pack(side="right")

        # Columnas
        cols_frame = ctk.CTkFrame(frame, fg_color=UI["color_bg"], corner_radius=6)
        cols_frame.pack(fill="x", padx=15, pady=(5, 0))

        for col, texto, ancho in [
            (0, "TICKET",   100),
            (1, "PLACA",    80),
            (2, "CONDUCTOR",140),
            (3, "BRUTO(KG)",90),
            (4, "ENTRADA",  120),
        ]:
            ctk.CTkLabel(
                cols_frame, text=texto,
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color=UI["color_muted"],
                width=ancho, anchor="w"
            ).grid(row=0, column=col, padx=8, pady=5, sticky="w")

        # Scroll para la lista
        scroll = ctk.CTkScrollableFrame(
            frame, fg_color="transparent", height=250
        )
        scroll.pack(fill="both", expand=True, padx=15, pady=5)

        if not pendientes:
            ctk.CTkLabel(
                scroll,
                text="✅ No hay camiones en planta",
                font=ctk.CTkFont(size=13),
                text_color=UI["color_muted"]
            ).pack(pady=30)
        else:
            for i, p in enumerate(pendientes):
                bg = UI["color_card"] if i % 2 == 0 else UI["color_bg"]
                fila = ctk.CTkFrame(scroll, fg_color=bg, corner_radius=6)
                fila.pack(fill="x", pady=1)

                datos = [
                    p.numero_ticket,
                    p.vehiculo.placa if p.vehiculo else "-",
                    (p.conductor.nombre[:15] if p.conductor else "-"),
                    f"{float(p.peso_bruto or 0):,.0f}",
                    p.fecha_entrada.strftime("%H:%M:%S") if p.fecha_entrada else "-"
                ]
                anchos = [100, 80, 140, 90, 120]

                for col, (dato, ancho) in enumerate(zip(datos, anchos)):
                    ctk.CTkLabel(
                        fila, text=dato,
                        font=ctk.CTkFont(size=12),
                        text_color=UI["color_text"],
                        width=ancho, anchor="w"
                    ).grid(row=0, column=col, padx=8, pady=6, sticky="w")

                # Botón acción rápida
                ctk.CTkButton(
                    fila,
                    text="↑ Salida",
                    width=70,
                    height=26,
                    font=ctk.CTkFont(size=11),
                    command=lambda: self.callback_navegar("pesaje_salida"),
                    fg_color=UI["color_success"],
                    hover_color=UI["color_success_hover"]
                ).grid(row=0, column=5, padx=5, pady=4)

    def _refrescar(self):
        """Reconstruye el dashboard para mostrar datos actualizados."""
        for widget in self.winfo_children():
            widget.destroy()
        self._construir()
