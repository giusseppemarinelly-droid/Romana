# ============================================================
# gui/components/ui_kit.py — Componentes base del sistema de diseño
# ============================================================
# Ver docs/design-system.md para la spec completa. Toda pantalla nueva
# (o rediseñada) debería armarse con estos en vez de estilizar
# ctk.CTkButton/CTkFrame a mano cada vez -- es la diferencia entre un
# sistema de diseño de verdad y "los mismos valores copiados y pegados
# en cada pantalla".
#
# Puramente capa visual: nada acá conoce de báscula, HTTP ni base de
# datos. PesoDisplay/BadgeEstado reciben el peso/estado ya resuelto por
# la pantalla que los usa.

import customtkinter as ctk
from config import UI


def ocultar_scrollbar(scrollable_frame: ctk.CTkScrollableFrame):
    """
    Saca la barra de scroll visible de un CTkScrollableFrame sin
    perder el scroll en sí -- el mouse wheel sigue funcionando porque
    CTkScrollableFrame lo ata con bind_all() a nivel de aplicación, no
    al widget de la barra (ver customtkinter/windows/widgets/
    ctk_scrollable_frame.py, _mouse_wheel_all). Hallazgo de sesión
    (2026-09-16): esa barra angosta se sumaba al mismo bug de redibujado
    en negro de CTkScrollableFrame sobre Windows que ya veníamos viendo
    en el sidebar -- sacarla reduce la superficie de canvases que
    CustomTkinter tiene que repintar.

    Usa el atributo interno _scrollbar (no hay API pública para esto en
    customtkinter 5.2.2) -- se llama una sola vez, justo después de
    construir el frame: _create_grid() solo lo posiciona una vez en
    __init__, nada más adelante lo vuelve a gridear, así que
    grid_remove() queda firme para toda la vida del widget.
    """
    try:
        scrollable_frame._scrollbar.grid_remove()
    except Exception:
        pass
    return scrollable_frame


def _fuente(nivel: str, weight: str = "normal") -> ctk.CTkFont:
    """Fuente de la escala tipográfica del sistema (ver design-system.md)."""
    tamaños = {
        "display": UI["fuente_display"],
        "h1": UI["fuente_h1"],
        "h2": UI["fuente_h2"],
        "body": UI["fuente_body"],
        "label": UI["fuente_label"],
        "caption": UI["fuente_caption"],
    }
    return ctk.CTkFont(family=UI["fuente"], size=tamaños[nivel], weight=weight)


# ============================================================
# BOTONES
# ============================================================
def boton_primario(parent, text, command=None, height=40, **kwargs) -> ctk.CTkButton:
    """Botón de acción principal de la pantalla (Registrar, Guardar, Capturar)."""
    return ctk.CTkButton(
        parent, text=text, command=command, height=height,
        corner_radius=UI["radio_control"],
        fg_color=UI["color_accent"], hover_color=UI["color_accent_hover"],
        text_color="#FFFFFF",
        font=_fuente("body", "bold"),
        **kwargs,
    )


def boton_secundario(parent, text, command=None, height=40, **kwargs) -> ctk.CTkButton:
    """Botón de acción secundaria (Buscar, Actualizar, Cancelar)."""
    return ctk.CTkButton(
        parent, text=text, command=command, height=height,
        corner_radius=UI["radio_control"],
        fg_color="transparent", hover_color=UI["color_bg"],
        border_width=1, border_color=UI["color_border"],
        text_color=UI["color_brand"],
        font=_fuente("body"),
        **kwargs,
    )


def boton_peligro(parent, text, command=None, height=40, **kwargs) -> ctk.CTkButton:
    """Botón de acción destructiva/crítica (Anular, Rechazar, Eliminar)."""
    return ctk.CTkButton(
        parent, text=text, command=command, height=height,
        corner_radius=UI["radio_control"],
        fg_color=UI["color_danger"], hover_color=UI["color_danger_hover"],
        text_color="#FFFFFF",
        font=_fuente("body", "bold"),
        **kwargs,
    )


# ============================================================
# TEXTO
# ============================================================
def titulo_h1(parent, text, **kwargs) -> ctk.CTkLabel:
    """Título de pantalla."""
    return ctk.CTkLabel(parent, text=text, font=_fuente("h1", "bold"),
                         text_color=UI["color_brand"], **kwargs)


def titulo_h2(parent, text, **kwargs) -> ctk.CTkLabel:
    """Título de sección dentro de una tarjeta."""
    return ctk.CTkLabel(parent, text=text, font=_fuente("h2", "bold"),
                         text_color=UI["color_text"], **kwargs)


def etiqueta_campo(parent, text, **kwargs) -> ctk.CTkLabel:
    """Etiqueta de campo de formulario -- mayúsculas, espaciada, chica."""
    return ctk.CTkLabel(parent, text=text.upper(), font=_fuente("label", "bold"),
                         text_color=UI["color_muted"], **kwargs)


def texto_ayuda(parent, text, **kwargs) -> ctk.CTkLabel:
    """Texto secundario/de ayuda (caption)."""
    return ctk.CTkLabel(parent, text=text, font=_fuente("caption"),
                         text_color=UI["color_muted"], **kwargs)


# ============================================================
# CARD
# ============================================================
class Card(ctk.CTkFrame):
    """Contenedor base para agrupar contenido -- fondo blanco, borde
    fino en vez de sombra (ver design-system.md, sección Elevación)."""

    def __init__(self, parent, **kwargs):
        defaults = dict(
            fg_color=UI["color_card"],
            border_color=UI["color_border"], border_width=1,
            corner_radius=UI["radio_card"],
        )
        defaults.update(kwargs)
        super().__init__(parent, **defaults)


# ============================================================
# BADGE DE ESTADO (báscula y en general)
# ============================================================
# Hallazgo pendiente de la auditoría (C-05): mostrar siempre qué está
# pasando con el display, no solo en la consola. Nunca solo color --
# siempre punto + texto.
_ESTADOS_BASCULA = {
    "conectada": {
        "texto": "PESO ESTABLE",
        "color": "color_bascula_ok",
        "relleno": True,
    },
    "leyendo": {
        "texto": "Estabilizando…",
        "color": "color_bascula_leyendo",
        "relleno": True,
    },
    "sin_senal": {
        "texto": "Sin señal",
        "color": "color_bascula_sin_senal",
        "relleno": False,
    },
    "error": {
        "texto": "⚠ Error de báscula",
        "color": "color_bascula_error",
        "relleno": True,
    },
}


class BadgeEstado(ctk.CTkFrame):
    """Pill de estado: punto de color + texto. `estado` es una de las
    claves de _ESTADOS_BASCULA, o se puede pasar texto/color a mano
    para otros usos (aprobado/rechazado, etc.) vía `texto`/`color_hex`."""

    def __init__(self, parent, estado: str = "sin_senal",
                 texto: str = None, color_hex: str = None, **kwargs):
        super().__init__(parent, fg_color=UI["color_bg"],
                          corner_radius=UI["radio_control"], **kwargs)
        self.grid_columnconfigure(1, weight=1)

        self._punto = ctk.CTkLabel(
            self, text="●", font=ctk.CTkFont(size=11),
            width=14,
        )
        self._punto.grid(row=0, column=0, padx=(10, 2), pady=6)

        self._texto = ctk.CTkLabel(
            self, text="", font=_fuente("caption", "bold"),
        )
        self._texto.grid(row=0, column=1, padx=(0, 12), pady=6, sticky="w")

        self.actualizar(estado, texto, color_hex)

    def actualizar(self, estado: str = "sin_senal", texto: str = None, color_hex: str = None):
        info = _ESTADOS_BASCULA.get(estado, _ESTADOS_BASCULA["sin_senal"])
        color = color_hex or UI[info["color"]]
        self._punto.configure(
            text="●" if info.get("relleno", True) else "○",
            text_color=color,
        )
        self._texto.configure(text=texto or info["texto"], text_color=color)


# ============================================================
# PESO DISPLAY -- el elemento más prominente de las pantallas de pesaje
# ============================================================
class PesoDisplay(ctk.CTkFrame):
    """
    El número de peso en tipografía `display` (44px, la más grande de
    toda la app) + el badge de estado de la báscula debajo. Cada
    pantalla de captura (Entrada/Salida/Completar) instancia una de
    estas y la actualiza con `.set_peso()` -- el componente no sabe
    nada de báscula ni de hilos, solo de cómo mostrar el número.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)

        self._lbl_peso = ctk.CTkLabel(
            self, text="—— KG",
            font=_fuente("display", "bold"),
            text_color=UI["color_brand"],
        )
        self._lbl_peso.grid(row=0, column=0, pady=(4, 8))

        self.badge = BadgeEstado(self, estado="sin_senal")
        self.badge.grid(row=1, column=0, pady=(0, 4))

    def set_peso(self, peso, estable: bool):
        """peso=None -> sin señal. peso numérico -> estable/leyendo según `estable`."""
        if peso is None:
            self._lbl_peso.configure(text="—— KG", text_color=UI["color_muted"])
            self.badge.actualizar("sin_senal")
            return

        color = UI["color_bascula_ok"] if estable else UI["color_bascula_leyendo"]
        self._lbl_peso.configure(text=f"{peso:,.0f} KG", text_color=color)
        self.badge.actualizar("conectada" if estable else "leyendo")

    def set_error(self, mensaje: str = None):
        """Estado de error explícito (dato corrupto, hardware) -- distinto de "sin señal"."""
        self._lbl_peso.configure(text="—— KG", text_color=UI["color_danger"])
        self.badge.actualizar("error", texto=mensaje)
