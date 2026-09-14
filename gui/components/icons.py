# ============================================================
# gui/components/icons.py — Set de íconos propio (línea fina, un color)
# ============================================================
# Reemplaza los emoji del sidebar (🏠 🚛 👤 🏭 ...) -- se ven
# inconsistentes entre sí (cada uno con su propio estilo/color de
# fuente de emoji de Windows) y "genéricos". Estos se dibujan a mano
# con Pillow (ya es dependencia del proyecto, usada para el logo/ícono
# de ventana -- no se agrega nada nuevo) como siluetas simples de un
# solo color, mismo grosor de trazo en todos, mismo estilo -- se leen
# como un set de verdad, no como una mezcla de símbolos sueltos.
#
# Cada ícono se dibuja a 4x el tamaño final y se reduce con LANCZOS
# (antialiasing parejo en líneas diagonales/curvas) -- a 18-20px reales
# una línea de 1 solo píxel sin antialiasing se ve dentada.
#
# Uso: icono("dashboard", color=UI["color_sidebar_text"], size=18)
# devuelve un ctk.CTkImage listo para pasar a CTkButton(image=...).

import customtkinter as ctk
from PIL import Image, ImageDraw

_FACTOR = 4          # supersampling
_GROSOR = 1.8         # grosor de trazo, en px del tamaño FINAL (no del supersample)
_cache = {}           # (nombre, color, size) -> CTkImage, se piden seguido (cada redraw de sidebar)


def icono(nombre: str, color: str, size: int = 18) -> ctk.CTkImage:
    clave = (nombre, color, size)
    if clave in _cache:
        return _cache[clave]

    hi = size * _FACTOR
    img = Image.new("RGBA", (hi, hi), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    grosor = max(1, round(_GROSOR * _FACTOR))

    dibujante = _ICONOS.get(nombre)
    if dibujante is None:
        raise ValueError(f"Ícono desconocido: {nombre!r}")
    dibujante(draw, hi, color, grosor)

    img = img.resize((size, size), Image.LANCZOS)
    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    _cache[clave] = ctk_img
    return ctk_img


# ---- helpers de dibujo -----------------------------------------------
def _margen(hi, frac=0.14):
    return round(hi * frac)


# ---- cada ícono, en un cuadrado hi×hi con margen ya aplicado ----------
def _dashboard(d, hi, c, g):
    m = _margen(hi, 0.10)
    # Techo (triángulo) + casa (rectángulo) -- silueta de casa simple
    d.line([(m, hi * 0.5), (hi / 2, m), (hi - m, hi * 0.5)], fill=c, width=g, joint="curve")
    d.line([(hi * 0.22, hi * 0.46), (hi * 0.22, hi - m)], fill=c, width=g)
    d.line([(hi * 0.78, hi * 0.46), (hi * 0.78, hi - m)], fill=c, width=g)
    d.line([(hi * 0.22, hi - m), (hi * 0.78, hi - m)], fill=c, width=g)
    # Puerta
    d.rectangle([hi * 0.42, hi * 0.62, hi * 0.58, hi - m], outline=c, width=g)


def _entrada(d, hi, c, g):
    # Bandeja abajo + flecha entrando desde arriba (icono clásico de "inbox")
    cx = hi / 2
    d.line([(hi * 0.18, hi * 0.65), (hi * 0.18, hi * 0.82), (hi * 0.82, hi * 0.82), (hi * 0.82, hi * 0.65)],
           fill=c, width=g, joint="curve")
    d.line([(cx, hi * 0.14), (cx, hi * 0.62)], fill=c, width=g)
    d.line([(cx - hi * 0.16, hi * 0.46), (cx, hi * 0.62), (cx + hi * 0.16, hi * 0.46)], fill=c, width=g, joint="curve")


def _salida(d, hi, c, g):
    cx = hi / 2
    d.line([(hi * 0.18, hi * 0.65), (hi * 0.18, hi * 0.82), (hi * 0.82, hi * 0.82), (hi * 0.82, hi * 0.65)],
           fill=c, width=g, joint="curve")
    d.line([(cx, hi * 0.62), (cx, hi * 0.14)], fill=c, width=g)
    d.line([(cx - hi * 0.16, hi * 0.30), (cx, hi * 0.14), (cx + hi * 0.16, hi * 0.30)], fill=c, width=g, joint="curve")


def _completar(d, hi, c, g):
    m = _margen(hi, 0.16)
    d.ellipse([m, m, hi - m, hi - m], outline=c, width=g)
    d.line([(hi * 0.32, hi * 0.52), (hi * 0.45, hi * 0.66), (hi * 0.70, hi * 0.36)],
           fill=c, width=g, joint="curve")


def _kardex(d, hi, c, g):
    m = _margen(hi, 0.16)
    d.rectangle([m, m, hi - m, hi - m], outline=c, width=g)
    for frac in (0.38, 0.55, 0.72):
        d.line([(m + hi * 0.12, hi * frac), (hi - m - hi * 0.12, hi * frac)], fill=c, width=max(1, g - _FACTOR // 2))


def _corte(d, hi, c, g):
    # Tijeras: dos "mangos" (círculos) unidos por líneas que cruzan en X
    cx, cy = hi * 0.5, hi * 0.5
    r = hi * 0.11
    for cxo, cyo in ((hi * 0.22, hi * 0.78), (hi * 0.22, hi * 0.22)):
        d.ellipse([cxo - r, cyo - r, cxo + r, cyo + r], outline=c, width=g)
    d.line([(hi * 0.30, hi * 0.72), (hi * 0.82, hi * 0.20)], fill=c, width=g)
    d.line([(hi * 0.30, hi * 0.28), (hi * 0.82, hi * 0.80)], fill=c, width=g)


def _aprobaciones(d, hi, c, g):
    m = _margen(hi, 0.18)
    d.rounded_rectangle([m, hi * 0.10, hi - m, hi - m], radius=hi * 0.05, outline=c, width=g)
    d.rounded_rectangle([hi * 0.38, m * 0.4, hi * 0.62, hi * 0.16], radius=hi * 0.02, outline=c, width=g)
    d.line([(hi * 0.34, hi * 0.55), (hi * 0.46, hi * 0.67), (hi * 0.68, hi * 0.40)],
           fill=c, width=g, joint="curve")


def _vehiculos(d, hi, c, g):
    base = hi * 0.68
    d.rectangle([hi * 0.10, hi * 0.34, hi * 0.62, base], outline=c, width=g)
    d.line([(hi * 0.62, hi * 0.46), (hi * 0.82, hi * 0.46), (hi * 0.90, base), (hi * 0.62, base)],
           fill=c, width=g, joint="curve")
    r = hi * 0.09
    for cxo in (hi * 0.28, hi * 0.76):
        d.ellipse([cxo - r, base - r, cxo + r, base + r], outline=c, width=g)


def _conductores(d, hi, c, g):
    cx = hi / 2
    r = hi * 0.16
    d.ellipse([cx - r, hi * 0.16, cx + r, hi * 0.16 + 2 * r], outline=c, width=g)
    d.arc([hi * 0.16, hi * 0.55, hi * 0.84, hi * 1.10], start=200, end=340, fill=c, width=g)


def _proveedores(d, hi, c, g):
    m = _margen(hi, 0.14)
    base = hi - m
    d.rectangle([m, hi * 0.30, hi - m, base], outline=c, width=g)
    for cxo in (hi * 0.30, hi * 0.5, hi * 0.70):
        d.rectangle([cxo - hi * 0.05, hi * 0.14, cxo + hi * 0.05, hi * 0.30], outline=c, width=g)


def _transportistas(d, hi, c, g):
    # Ruta: línea de trazos con un punto de origen y uno de destino
    d.ellipse([hi * 0.12, hi * 0.62, hi * 0.28, hi * 0.78], outline=c, width=g)
    d.ellipse([hi * 0.72, hi * 0.22, hi * 0.88, hi * 0.38], outline=c, width=g)
    puntos = [(hi * 0.30, hi * 0.66), (hi * 0.45, hi * 0.50), (hi * 0.55, hi * 0.50), (hi * 0.70, hi * 0.32)]
    for i in range(0, len(puntos) - 1, 2):
        d.line([puntos[i], puntos[i + 1]], fill=c, width=g)


def _productos(d, hi, c, g):
    m = _margen(hi, 0.16)
    cx = hi / 2
    d.line([(m, hi * 0.32), (cx, hi * 0.16), (hi - m, hi * 0.32),
            (hi - m, hi * 0.76), (cx, hi * 0.92), (m, hi * 0.76), (m, hi * 0.32)],
           fill=c, width=g, joint="curve")
    d.line([(m, hi * 0.32), (cx, hi * 0.48), (hi - m, hi * 0.32)], fill=c, width=g, joint="curve")
    d.line([(cx, hi * 0.48), (cx, hi * 0.92)], fill=c, width=g)


def _destinos(d, hi, c, g):
    cx = hi / 2
    r = hi * 0.24
    cy = hi * 0.40
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=c, width=g)
    d.line([(cx, cy + r * 0.6), (cx, hi * 0.90)], fill=c, width=g)
    r2 = hi * 0.08
    d.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], outline=c, width=max(1, g - _FACTOR // 2))


def _usuarios(d, hi, c, g):
    r = hi * 0.13
    for dx in (-0.15, 0.15):
        cx = hi * (0.5 + dx)
        d.ellipse([cx - r, hi * 0.18, cx + r, hi * 0.18 + 2 * r], outline=c, width=g)
        d.arc([cx - r * 1.9, hi * 0.52, cx + r * 1.9, hi * 0.95], start=200, end=340, fill=c, width=g)


def _configuracion(d, hi, c, g):
    cx, cy = hi / 2, hi / 2
    r_ext, r_int = hi * 0.34, hi * 0.14
    import math
    dientes = 8
    for i in range(dientes):
        ang = (2 * math.pi / dientes) * i
        x1, y1 = cx + r_ext * 0.78 * math.cos(ang), cy + r_ext * 0.78 * math.sin(ang)
        x2, y2 = cx + r_ext * math.cos(ang), cy + r_ext * math.sin(ang)
        d.line([(x1, y1), (x2, y2)], fill=c, width=g * 2)
    d.ellipse([cx - r_ext * 0.62, cy - r_ext * 0.62, cx + r_ext * 0.62, cy + r_ext * 0.62], outline=c, width=g)
    d.ellipse([cx - r_int, cy - r_int, cx + r_int, cy + r_int], outline=c, width=g)


def _balanza(d, hi, c, g):
    """Logo de la app -- una balanza/romana simple, reemplaza el emoji ⚖."""
    cx = hi / 2
    d.line([(cx, hi * 0.10), (cx, hi * 0.86)], fill=c, width=g)
    d.line([(hi * 0.16, hi * 0.24), (hi * 0.84, hi * 0.24)], fill=c, width=g)
    for cxo in (hi * 0.16, hi * 0.84):
        d.line([(cxo, hi * 0.24), (cxo - hi * 0.10, hi * 0.42)], fill=c, width=g)
        d.line([(cxo, hi * 0.24), (cxo + hi * 0.10, hi * 0.42)], fill=c, width=g)
        d.arc([cxo - hi * 0.12, hi * 0.34, cxo + hi * 0.12, hi * 0.50], start=0, end=180, fill=c, width=g)
    d.line([(hi * 0.30, hi * 0.86), (hi * 0.70, hi * 0.86)], fill=c, width=g)


_ICONOS = {
    "dashboard": _dashboard,
    "entrada": _entrada,
    "salida": _salida,
    "completar": _completar,
    "kardex": _kardex,
    "corte": _corte,
    "aprobaciones": _aprobaciones,
    "vehiculos": _vehiculos,
    "conductores": _conductores,
    "proveedores": _proveedores,
    "transportistas": _transportistas,
    "productos": _productos,
    "destinos": _destinos,
    "usuarios": _usuarios,
    "configuracion": _configuracion,
    "balanza": _balanza,
}
