# ============================================================
# gui/app.py — Ventana principal y navegación del sistema
# ============================================================
# Esta es la "columna vertebral" de la interfaz gráfica.
# Gestiona:
#   - La ventana principal (frame que contiene todo)
#   - La navegación entre pantallas (login → dashboard → módulos)
#   - El menú lateral
#   - El header con información del usuario

import customtkinter as ctk
from config import EMPRESA, UI

# Configurar apariencia de CustomTkinter
ctk.set_appearance_mode(UI["tema"])       # "dark" o "light"
ctk.set_default_color_theme("blue")       # Tema de color base


class App(ctk.CTk):
    """
    Ventana principal del sistema de Romana.
    Hereda de CTk (CustomTkinter) que es la ventana raíz.

    Arquitectura de navegación:
    ┌─────────────────────────────────────────┐
    │  App (ventana raíz)                      │
    │  ┌────────────────────────────────────┐  │
    │  │  LoginView (mientras no hay sesión)│  │
    │  └────────────────────────────────────┘  │
    │  ┌─────────┬──────────────────────────┐  │
    │  │  Sidebar│  ContentArea             │  │
    │  │  (menú) │  (pantalla activa)       │  │
    │  └─────────┴──────────────────────────┘  │
    └─────────────────────────────────────────┘
    """

    def __init__(self):
        # CTk (en Windows) hace su propio withdraw()/update()/deiconify()
        # al arrancar para pintar la barra de título oscura -- esa
        # coreografía interna (ver customtkinter/windows/ctk_tk.py,
        # _windows_set_titlebar_color) competía con el pedido de pantalla
        # completa de más abajo y la ventana terminaba apareciendo en su
        # tamaño normal, con bordes, en vez de fullscreen. Desactivarla
        # evita el conflicto (se pierde el detalle cosmético de la barra
        # oscura, no afecta nada funcional).
        self._deactivate_windows_window_header_manipulation = True
        super().__init__()

        # --- Configuración de la ventana ---
        self.title(f"🚛 Romana — {EMPRESA['nombre']}")
        self.geometry("1280x780")
        self.minsize(1024, 680)

        # Centrar la ventana (por si el usuario la restaura con doble
        # clic en la barra de título) y arrancar maximizada -- ventana
        # normal con bordes y barra de título, ocupando toda la
        # pantalla (no fullscreen sin bordes).
        self._centrar_ventana()
        self.state("zoomed")

        # F11 alterna pantalla completa sin bordes (kiosko); Esc sale de
        # ella y vuelve a la ventana maximizada normal.
        self.bind("<F11>", lambda e: self.attributes(
            "-fullscreen", not self.attributes("-fullscreen")))
        self.bind("<Escape>", lambda e: self.attributes("-fullscreen", False))

        # --- Estado de la aplicación ---
        self._pantalla_actual = None   # Frame de la pantalla activa
        self._sidebar = None           # Menú lateral
        self._header = None            # Barra superior
        self._content_frame = None     # Área de contenido

        # --- Mostrar pantalla de login primero ---
        self._mostrar_login()

    def _centrar_ventana(self):
        """Centra la ventana en el monitor."""
        self.update_idletasks()
        ancho = 1280
        alto = 780
        x = (self.winfo_screenwidth() // 2) - (ancho // 2)
        y = (self.winfo_screenheight() // 2) - (alto // 2)
        self.geometry(f"{ancho}x{alto}+{x}+{y}")

    def _limpiar_ventana(self):
        """Elimina todos los widgets actuales de la ventana."""
        for widget in self.winfo_children():
            widget.destroy()
        self._sidebar = None
        self._header = None
        self._content_frame = None
        self._pantalla_actual = None

    # ==========================================================
    # NAVEGACIÓN
    # ==========================================================

    def _mostrar_login(self):
        """Muestra la pantalla de login."""
        self._limpiar_ventana()
        from gui.login_view import LoginView
        login = LoginView(self, callback_login=self._on_login_exitoso)
        login.pack(fill="both", expand=True)

    def _on_login_exitoso(self):
        """
        Callback que se llama cuando el login fue exitoso.
        Si es nivel 4 (CC), va directo a la vista de aprobaciones.
        """
        from client.api_client import api_client
        usuario = api_client.usuario
        self._mostrar_dashboard()
        # Redirigir CC directamente a su vista
        if usuario and usuario["nivel"] == 4:
            self.navegar("centro_costos")

    def _mostrar_dashboard(self):
        """
        Construye el layout principal con sidebar + header + contenido.
        """
        self._limpiar_ventana()
        self._construir_layout_principal()
        # La primera pantalla que se muestra es el dashboard
        self.navegar("dashboard")

    def _construir_layout_principal(self):
        """
        Construye el layout de 3 columnas:
         [Sidebar] | [Header + ContentArea]
        """
        # Frame raíz que divide sidebar y contenido
        self._main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._main_frame.pack(fill="both", expand=True)
        self._main_frame.grid_columnconfigure(1, weight=1)
        self._main_frame.grid_rowconfigure(0, weight=1)

        # --- Sidebar (menú lateral izquierdo) ---
        from gui.components.sidebar import Sidebar
        self._sidebar = Sidebar(
            self._main_frame,
            callback_navegar=self.navegar,
            callback_logout=self._on_logout
        )
        self._sidebar.grid(row=0, column=0, sticky="nsew")

        # --- Área derecha: header + contenido ---
        derecha = ctk.CTkFrame(self._main_frame, fg_color="transparent")
        derecha.grid(row=0, column=1, sticky="nsew")
        derecha.grid_rowconfigure(1, weight=1)
        derecha.grid_columnconfigure(0, weight=1)

        # Header superior
        from gui.components.header import Header
        self._header = Header(derecha, callback_logout=self._on_logout)
        self._header.grid(row=0, column=0, sticky="ew")

        # Área de contenido (aquí se cargan las pantallas)
        self._content_frame = ctk.CTkFrame(derecha, fg_color=UI["color_bg"])
        self._content_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self._content_frame.grid_columnconfigure(0, weight=1)
        self._content_frame.grid_rowconfigure(0, weight=1)

    def navegar(self, destino: str):
        """
        Navega a una pantalla específica.

        Args:
            destino: Nombre de la pantalla.
                     Valores válidos: "dashboard", "pesaje_entrada",
                     "pesaje_salida", "kardex", "vehiculos",
                     "conductores", "proveedores", "empresas_transportistas",
                     "productos", "destinos", "usuarios", "configuracion"
        """
        if not self._content_frame:
            return

        # Cada pantalla carga sus datos con llamadas HTTP síncronas en
        # el hilo principal de Tkinter durante su construcción (no hay
        # spinner ni feedback propio) -- un cursor de espera visible
        # convierte esa pausa en algo intencional en vez de una
        # ventana que "no responde" sin explicación. update_idletasks()
        # fuerza a pintar el cursor ANTES de la llamada bloqueante.
        self.configure(cursor="watch")
        self.update_idletasks()

        # Destruir pantalla actual
        if self._pantalla_actual:
            self._pantalla_actual.destroy()

        # Marcar el botón activo en el sidebar
        if self._sidebar:
            self._sidebar.marcar_activo(destino)

        # Actualizar título en el header
        titulos = {
            "dashboard":         "📊 Dashboard",
            "pesaje_entrada":    "↓ Entrada de Camión",
            "pesaje_salida":     "↑ Salida / Capturar Peso",
            "completar_pesaje":  "✔ Completar Pesaje",
            "centro_costos":     "📋 Centro de Costos — Aprobaciones",
            "kardex":            "📋 Kardex de Pesadas",
            "corte":             "✂ Corte de Pesadas",
            "vehiculos":         "🚛 Vehículos",
            "conductores":       "👤 Conductores",
            "proveedores":       "🏭 Proveedores",
            "empresas_transportistas": "🚚 Empresas Transportistas",
            "productos":         "📦 Productos",
            "destinos":          "📍 Destinos",
            "lotes":             "🗂 Lotes",
            "remolques":         "🚜 Remolques",
            "contenedores":      "📫 Contenedores",
            "usuarios":          "👥 Usuarios",
            "configuracion":     "⚙ Configuración",
        }
        if self._header:
            self._header.actualizar_titulo(titulos.get(destino, destino))

        # Cargar la pantalla correspondiente
        try:
            pantalla = self._crear_pantalla(destino, self._content_frame)
            if pantalla:
                pantalla.grid(row=0, column=0, sticky="nsew")
                self._pantalla_actual = pantalla
        finally:
            self.configure(cursor="")

    def _crear_pantalla(self, destino: str, parent) -> ctk.CTkFrame:
        """Factory de pantallas. Crea y retorna el frame de la pantalla pedida."""
        try:
            if destino == "dashboard":
                from gui.dashboard_view import DashboardView
                return DashboardView(parent, callback_navegar=self.navegar)

            elif destino == "pesaje_entrada":
                from gui.pesaje.pesaje_entrada_view import PesajeEntradaView
                return PesajeEntradaView(parent, callback_navegar=self.navegar)

            elif destino == "pesaje_salida":
                from gui.pesaje.pesaje_salida_view import PesajeSalidaView
                return PesajeSalidaView(parent, callback_navegar=self.navegar)

            elif destino == "completar_pesaje":
                from gui.pesaje.completar_pesaje_view import CompletarPesajeView
                return CompletarPesajeView(parent, callback_navegar=self.navegar)

            elif destino == "centro_costos":
                from gui.centro_costos.centro_costos_view import CentroCostosView
                return CentroCostosView(parent, callback_navegar=self.navegar)

            elif destino == "kardex":
                from gui.pesaje.kardex_view import KardexView
                return KardexView(parent)

            elif destino == "corte":
                from gui.pesaje.corte_view import CorteView
                return CorteView(parent)

            elif destino == "vehiculos":
                from gui.maestros.vehiculos_view import VehiculosView
                return VehiculosView(parent)

            elif destino == "conductores":
                from gui.maestros.conductores_view import ConductoresView
                return ConductoresView(parent)

            elif destino == "proveedores":
                from gui.maestros.proveedores_view import ProveedoresView
                return ProveedoresView(parent)

            elif destino == "empresas_transportistas":
                from gui.maestros.empresas_transportistas_view import EmpresasTransportistasView
                return EmpresasTransportistasView(parent)

            elif destino == "productos":
                from gui.maestros.productos_view import ProductosView
                return ProductosView(parent)

            elif destino == "destinos":
                from gui.maestros.destinos_view import DestinosView
                return DestinosView(parent)

            elif destino == "usuarios":
                from gui.admin.usuarios_view import UsuariosView
                return UsuariosView(parent)

            elif destino == "configuracion":
                from gui.admin.configuracion_view import ConfiguracionView
                return ConfiguracionView(parent)

            else:
                # Pantalla temporal para módulos no implementados aún
                frame = ctk.CTkFrame(parent, fg_color="transparent")
                ctk.CTkLabel(
                    frame,
                    text=f"🚧 Módulo '{destino}' en construcción",
                    font=ctk.CTkFont(family=UI["fuente"], size=20)
                ).pack(expand=True)
                return frame

        except Exception as e:
            # Si hay error al cargar la pantalla, mostrar el error
            frame = ctk.CTkFrame(parent, fg_color="transparent")
            ctk.CTkLabel(
                frame,
                text=f"❌ Error al cargar pantalla '{destino}':\n{str(e)}",
                font=ctk.CTkFont(family=UI["fuente"], size=14),
                text_color="#FF6B6B"
            ).pack(expand=True, padx=20, pady=20)
            import traceback
            traceback.print_exc()
            return frame

    def _on_logout(self):
        """Cierra la sesión y vuelve al login."""
        from client.api_client import api_client
        api_client.logout()
        self._mostrar_login()
