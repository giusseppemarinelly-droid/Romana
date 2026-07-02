# ============================================================
# services/reporte_service.py — Generación de Reportes PDF y Excel
# ============================================================

import io
from datetime import datetime
from config import EMPRESA

# ---- ReportLab (PDF) ----
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# ---- OpenPyXL (Excel) ----
from openpyxl import Workbook
from openpyxl.styles import (
    Font, Alignment, PatternFill, Border, Side
)
from openpyxl.utils import get_column_letter


# =============================================================
# HELPERS
# =============================================================

def _fmt_fecha(dt) -> str:
    """Formatea un datetime o retorna '—'."""
    if dt:
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    return "—"


def _fmt_peso(val) -> str:
    """Formatea un peso o retorna '—'."""
    if val is not None:
        return f"{float(val):,.2f} KG"
    return "—"


# =============================================================
# TICKET DE PESAJE (PDF)
# =============================================================

def generar_ticket_pdf(pesada) -> bytes:
    """
    Genera el ticket de pesaje en PDF.

    El ticket incluye:
     - Encabezado con datos de la empresa
     - Número de ticket y fechas
     - Datos del vehículo, conductor, producto
     - Tabla de pesos (bruto, tara, neto)
     - Pie de ticket

    Args:
        pesada: Objeto Pesada de la base de datos

    Returns:
        Contenido del PDF en bytes (Romana y Centro de Costos son
        máquinas distintas sin disco compartido, así que el reporte se
        genera en el servidor y se transmite por HTTP en vez de
        escribirse a un archivo local).
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm
    )

    styles = getSampleStyleSheet()
    elements = []

    # ---- Colores ----
    AZUL     = colors.HexColor("#1E3A5F")
    AZUL_CLR = colors.HexColor("#1E90FF")
    GRIS     = colors.HexColor("#F5F5F5")
    VERDE    = colors.HexColor("#00703C")

    # ---- Encabezado: nombre empresa ----
    style_titulo = ParagraphStyle(
        "titulo", parent=styles["Normal"],
        fontSize=18, fontName="Helvetica-Bold",
        alignment=TA_CENTER, textColor=AZUL,
        spaceAfter=4
    )
    style_sub = ParagraphStyle(
        "sub", parent=styles["Normal"],
        fontSize=10, fontName="Helvetica",
        alignment=TA_CENTER, textColor=colors.grey,
        spaceAfter=2
    )

    elements.append(Paragraph(EMPRESA["nombre"], style_titulo))
    elements.append(Paragraph(f"RIF: {EMPRESA['rif']}", style_sub))
    elements.append(Paragraph(EMPRESA["direccion"], style_sub))
    elements.append(Paragraph(f"Tel: {EMPRESA['telefono']}", style_sub))
    elements.append(HRFlowable(width="100%", thickness=2, color=AZUL_CLR))
    elements.append(Spacer(1, 8))

    # ---- Número de ticket ----
    style_ticket_num = ParagraphStyle(
        "ticket_num", parent=styles["Normal"],
        fontSize=22, fontName="Helvetica-Bold",
        alignment=TA_CENTER, textColor=AZUL_CLR,
        spaceAfter=4
    )
    elements.append(Paragraph(f"TICKET DE PESAJE  {pesada.numero_ticket}", style_ticket_num))
    elements.append(Spacer(1, 8))

    # ---- Tabla de datos ----
    def fila(etiqueta, valor):
        return [
            Paragraph(f"<b>{etiqueta}</b>", styles["Normal"]),
            Paragraph(str(valor), styles["Normal"])
        ]

    datos_tabla = [
        fila("Fecha Entrada:",  _fmt_fecha(pesada.fecha_entrada)),
        fila("Fecha Salida:",   _fmt_fecha(pesada.fecha_salida)),
        fila("Vehículo (Placa):", pesada.vehiculo.placa if pesada.vehiculo else "—"),
        fila("Conductor:",      pesada.conductor.nombre if pesada.conductor else "—"),
        fila("Producto:",       pesada.producto.nombre if pesada.producto else "—"),
        fila("Proveedor:",      pesada.proveedor.nombre if pesada.proveedor else "—"),
        fila("Destino:",        pesada.destino.nombre if pesada.destino else "—"),
    ]
    if pesada.lote:
        datos_tabla.append(fila("Lote:", pesada.lote.codigo))
    if pesada.remolque:
        datos_tabla.append(fila("Remolque:", pesada.remolque.placa))
    if pesada.observaciones:
        datos_tabla.append(fila("Observaciones:", pesada.observaciones))

    tabla_datos = Table(datos_tabla, colWidths=[5*cm, 12*cm])
    tabla_datos.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), GRIS),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    elements.append(tabla_datos)
    elements.append(Spacer(1, 15))

    # ---- Tabla de PESOS (la más importante) ----
    style_peso_titulo = ParagraphStyle(
        "peso_titulo", parent=styles["Normal"],
        fontSize=11, fontName="Helvetica-Bold",
        alignment=TA_CENTER
    )

    pesos_data = [
        ["CONCEPTO", "PESO (KG)"],
        ["PESO BRUTO", f"{float(pesada.peso_bruto or 0):>12,.2f}"],
        ["PESO TARA",  f"{float(pesada.peso_tara or 0):>12,.2f}"],
        ["PESO NETO",  f"{float(pesada.peso_neto or 0):>12,.2f}"],
    ]

    tabla_pesos = Table(pesos_data, colWidths=[9*cm, 8*cm])
    tabla_pesos.setStyle(TableStyle([
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, 0), 12),
        ("ALIGN",      (0, 0), (-1, 0), "CENTER"),

        # Filas de datos
        ("FONTNAME",   (0, 1), (-1, -2), "Helvetica"),
        ("FONTSIZE",   (0, 1), (-1, -2), 11),
        ("ALIGN",      (1, 1), (1, -1),  "RIGHT"),

        # Fila NETO (destacada en verde)
        ("BACKGROUND", (0, -1), (-1, -1), VERDE),
        ("TEXTCOLOR",  (0, -1), (-1, -1), colors.white),
        ("FONTNAME",   (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",   (0, -1), (-1, -1), 14),

        # Padding
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),

        # Bordes
        ("GRID",       (0, 0), (-1, -1), 1, colors.grey),
        ("BOX",        (0, 0), (-1, -1), 2, AZUL),

        # Alternar filas
        ("BACKGROUND", (0, 1), (-1, 1), GRIS),
    ]))
    elements.append(tabla_pesos)
    elements.append(Spacer(1, 20))

    # ---- Pie del ticket ----
    style_pie = ParagraphStyle(
        "pie", parent=styles["Normal"],
        fontSize=9, fontName="Helvetica",
        alignment=TA_CENTER, textColor=colors.grey,
        spaceAfter=2
    )
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    elements.append(Spacer(1, 6))

    usr_entrada = pesada.usuario_entrada.nombre_completo if pesada.usuario_entrada else "—"
    usr_salida  = pesada.usuario_salida.nombre_completo  if pesada.usuario_salida  else "—"

    elements.append(Paragraph(
        f"Operador entrada: {usr_entrada}  |  Operador salida: {usr_salida}", style_pie))
    elements.append(Paragraph(
        f"Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M:%S')}", style_pie))
    elements.append(Paragraph(
        "Este ticket tiene validez como documento de pesaje oficial.", style_pie))

    # ---- Construir PDF ----
    doc.build(elements)
    return buffer.getvalue()


# =============================================================
# KARDEX DE PESADAS (PDF)
# =============================================================

def generar_kardex_pdf(pesadas: list, titulo: str = "Kardex de Pesadas") -> bytes:
    """
    Genera un reporte PDF del Kardex con la lista de pesadas.

    Args:
        pesadas: Lista de objetos Pesada
        titulo:  Título del reporte

    Returns:
        Contenido del PDF en bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=2*cm, bottomMargin=1.5*cm
    )

    styles = getSampleStyleSheet()
    elements = []

    AZUL = colors.HexColor("#1E3A5F")
    VERDE = colors.HexColor("#00703C")

    # Encabezado
    style_h = ParagraphStyle("h", parent=styles["Normal"],
        fontSize=14, fontName="Helvetica-Bold",
        alignment=TA_CENTER, textColor=AZUL)
    style_sub = ParagraphStyle("sub", parent=styles["Normal"],
        fontSize=9, fontName="Helvetica",
        alignment=TA_CENTER, textColor=colors.grey)

    elements.append(Paragraph(EMPRESA["nombre"], style_h))
    elements.append(Paragraph(titulo, style_h))
    elements.append(Paragraph(
        f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}  |  Total: {len(pesadas)} registros",
        style_sub))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=2, color=AZUL))
    elements.append(Spacer(1, 8))

    # Tabla de datos
    encabezados = ["Ticket", "Fecha", "Placa", "Producto", "Bruto KG", "Tara KG", "Neto KG", "Estado"]

    filas = [encabezados]
    total_neto = 0.0

    for p in pesadas:
        neto = float(p.peso_neto or 0)
        total_neto += neto
        filas.append([
            p.numero_ticket,
            _fmt_fecha(p.fecha_entrada)[:10],
            p.vehiculo.placa if p.vehiculo else "—",
            (p.producto.nombre[:12] if p.producto else "—"),
            f"{float(p.peso_bruto or 0):,.0f}",
            f"{float(p.peso_tara or 0):,.0f}",
            f"{neto:,.0f}",
            p.estado.upper()
        ])

    # Fila de totales
    filas.append([
        "", "TOTALES", "", "", "", "", f"{total_neto:,.0f}", f"{len(pesadas)} pesadas"
    ])

    col_widths = [2.8*cm, 2.5*cm, 2*cm, 3*cm, 2.2*cm, 2.2*cm, 2.2*cm, 2.1*cm]

    tabla = Table(filas, colWidths=col_widths, repeatRows=1)
    tabla.setStyle(TableStyle([
        # Encabezado
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, 0), 8),
        ("ALIGN",      (0, 0), (-1, 0), "CENTER"),

        # Cuerpo
        ("FONTNAME",   (0, 1), (-1, -2), "Helvetica"),
        ("FONTSIZE",   (0, 1), (-1, -2), 8),
        ("ALIGN",      (4, 1), (-1, -1), "RIGHT"),

        # Fila de totales
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E8F5E9")),
        ("FONTNAME",   (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",   (0, -1), (-1, -1), 9),

        # Alternado
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F9F9F9")]),

        # Bordes
        ("GRID",       (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("BOX",        (0, 0), (-1, -1), 1.5, AZUL),

        # Padding
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
    ]))

    elements.append(tabla)
    doc.build(elements)
    return buffer.getvalue()


# =============================================================
# KARDEX EN EXCEL
# =============================================================

def generar_kardex_excel(pesadas: list, titulo: str = "Kardex de Pesadas") -> bytes:
    """
    Genera el Kardex en formato Excel (.xlsx).

    Args:
        pesadas: Lista de objetos Pesada
        titulo:  Título del reporte

    Returns:
        Contenido del archivo Excel en bytes.
    """
    buffer = io.BytesIO()
    wb = Workbook()
    ws = wb.active
    ws.title = "Kardex"

    # ---- Estilos ----
    AZUL_OSCURO = "1E3A5F"
    AZUL_CLARO  = "1E90FF"
    VERDE       = "00703C"
    GRIS_CLARO  = "F5F5F5"
    GRIS_MEDIO  = "CCCCCC"

    font_titulo   = Font(name="Calibri", size=16, bold=True, color="FFFFFF")
    font_subtitulo= Font(name="Calibri", size=11, color="666666")
    font_header   = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    font_normal   = Font(name="Calibri", size=10)
    font_total    = Font(name="Calibri", size=11, bold=True)

    fill_header = PatternFill("solid", fgColor=AZUL_OSCURO)
    fill_total  = PatternFill("solid", fgColor="E8F5E9")
    fill_fila1  = PatternFill("solid", fgColor="FFFFFF")
    fill_fila2  = PatternFill("solid", fgColor=GRIS_CLARO)

    borde = Border(
        left=Side(style="thin", color=GRIS_MEDIO),
        right=Side(style="thin", color=GRIS_MEDIO),
        top=Side(style="thin", color=GRIS_MEDIO),
        bottom=Side(style="thin", color=GRIS_MEDIO)
    )

    # ---- Fila 1: Nombre empresa ----
    ws.merge_cells("A1:J1")
    ws["A1"] = EMPRESA["nombre"]
    ws["A1"].font = Font(name="Calibri", size=16, bold=True, color=AZUL_OSCURO)
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    # ---- Fila 2: Título del reporte ----
    ws.merge_cells("A2:J2")
    ws["A2"] = titulo
    ws["A2"].font = Font(name="Calibri", size=13, bold=True, color=AZUL_CLARO)
    ws["A2"].alignment = Alignment(horizontal="center")
    ws.row_dimensions[2].height = 22

    # ---- Fila 3: Fecha de generación ----
    ws.merge_cells("A3:J3")
    ws["A3"] = f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}  |  Total: {len(pesadas)} registros"
    ws["A3"].font = font_subtitulo
    ws["A3"].alignment = Alignment(horizontal="center")
    ws.row_dimensions[3].height = 18

    # ---- Fila 5: Encabezados de columnas ----
    columnas = [
        ("A", "TICKET",       15),
        ("B", "FECHA ENTRADA",20),
        ("C", "FECHA SALIDA", 20),
        ("D", "PLACA",        12),
        ("E", "CONDUCTOR",    22),
        ("F", "PRODUCTO",     22),
        ("G", "PROVEEDOR",    22),
        ("H", "BRUTO (KG)",   14),
        ("I", "TARA (KG)",    14),
        ("J", "NETO (KG)",    14),
    ]

    for col, nombre, ancho in columnas:
        celda = ws[f"{col}5"]
        celda.value = nombre
        celda.font = font_header
        celda.fill = fill_header
        celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        celda.border = borde
        ws.column_dimensions[col].width = ancho

    ws.row_dimensions[5].height = 28

    # ---- Datos ----
    total_neto = 0.0
    for i, p in enumerate(pesadas, start=6):
        neto = float(p.peso_neto or 0)
        total_neto += neto
        fill_fila = fill_fila1 if i % 2 == 0 else fill_fila2

        valores = [
            p.numero_ticket,
            _fmt_fecha(p.fecha_entrada),
            _fmt_fecha(p.fecha_salida),
            p.vehiculo.placa if p.vehiculo else "—",
            p.conductor.nombre if p.conductor else "—",
            p.producto.nombre if p.producto else "—",
            p.proveedor.nombre if p.proveedor else "—",
            float(p.peso_bruto or 0),
            float(p.peso_tara or 0),
            neto,
        ]

        for col_idx, valor in enumerate(valores, start=1):
            celda = ws.cell(row=i, column=col_idx, value=valor)
            celda.font = font_normal
            celda.fill = fill_fila
            celda.border = borde
            # Alinear pesos a la derecha
            if col_idx >= 8:
                celda.alignment = Alignment(horizontal="right")
                celda.number_format = "#,##0.00"

    # ---- Fila de totales ----
    fila_total = len(pesadas) + 6
    ws.cell(row=fila_total, column=1, value="TOTAL").font = font_total
    ws.cell(row=fila_total, column=10, value=total_neto).font = Font(
        name="Calibri", size=12, bold=True, color=VERDE)
    ws.cell(row=fila_total, column=10).number_format = "#,##0.00"

    for col_idx in range(1, 11):
        celda = ws.cell(row=fila_total, column=col_idx)
        celda.fill = fill_total
        celda.border = borde

    # ---- Congelar encabezado ----
    ws.freeze_panes = "A6"

    wb.save(buffer)
    return buffer.getvalue()
