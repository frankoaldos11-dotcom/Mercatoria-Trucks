import io
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOGO_PATH = os.path.join(_BASE_DIR, "static", "logo-mercatoria.jpg")

NARANJA = colors.HexColor("#F36B21")
GRIS_TEXTO = colors.HexColor("#333333")
GRIS_FONDO = colors.HexColor("#f7f7f7")


def _formato_fecha(raw):
    if not raw:
        return datetime.now().strftime("%d/%m/%Y")
    try:
        return datetime.strptime(str(raw)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return str(raw)[:10]


def _estilos():
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "DocTitulo", parent=base["Normal"],
            fontSize=16, fontName="Helvetica-Bold",
            textColor=NARANJA, alignment=TA_RIGHT,
        ),
        "numero": ParagraphStyle(
            "DocNumero", parent=base["Normal"],
            fontSize=12, fontName="Helvetica",
            textColor=colors.HexColor("#555555"), alignment=TA_RIGHT,
        ),
        "fecha": ParagraphStyle(
            "DocFecha", parent=base["Normal"],
            fontSize=10, textColor=colors.grey, alignment=TA_RIGHT,
        ),
        "label": ParagraphStyle(
            "Label", parent=base["Normal"],
            fontSize=8, fontName="Helvetica",
            textColor=colors.grey, spaceAfter=2,
        ),
        "valor": ParagraphStyle(
            "Valor", parent=base["Normal"],
            fontSize=11, fontName="Helvetica-Bold",
            textColor=GRIS_TEXTO, spaceAfter=4,
        ),
        "seccion": ParagraphStyle(
            "Seccion", parent=base["Normal"],
            fontSize=9, fontName="Helvetica-Bold",
            textColor=colors.white, leftIndent=8,
        ),
        "obs": ParagraphStyle(
            "Obs", parent=base["Normal"],
            fontSize=10, textColor=GRIS_TEXTO,
            leading=14,
        ),
        "firma_label": ParagraphStyle(
            "FirmaLabel", parent=base["Normal"],
            fontSize=9, textColor=colors.grey, alignment=TA_CENTER,
        ),
        "pie": ParagraphStyle(
            "Pie", parent=base["Normal"],
            fontSize=8, textColor=colors.grey, alignment=TA_CENTER,
        ),
    }


def _seccion(texto, estilo, ancho=17 * cm):
    t = Table([[Paragraph(texto, estilo)]], colWidths=[ancho])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NARANJA),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def _campo(label, valor, estilos):
    return [
        Paragraph(label.upper(), estilos["label"]),
        Paragraph(str(valor) if valor else "—", estilos["valor"]),
    ]


def generar_pdf_orden_carga(viaje: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2 * cm, leftMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )
    es = _estilos()
    elems = []

    # ── Cabecera ──────────────────────────────────────────────────────────────
    logo_cell = ""
    if os.path.exists(_LOGO_PATH):
        logo_cell = Image(_LOGO_PATH, width=5 * cm, height=2.5 * cm, kind="proportional")

    orden_id = viaje.get("id") or 0
    right_col = Table(
        [
            [Paragraph("ORDEN DE CARGA", es["titulo"])],
            [Paragraph(f"N° {orden_id:04d}", es["numero"])],
            [Paragraph(f"Fecha: {_formato_fecha(viaje.get('fecha_creacion'))}", es["fecha"])],
        ],
        colWidths=[8 * cm],
    )
    right_col.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (0, 0), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    cabecera = Table(
        [[logo_cell, right_col]],
        colWidths=[9 * cm, 8 * cm],
    )
    cabecera.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (1, 0), (1, 0), 0),
    ]))
    elems.append(cabecera)
    elems.append(HRFlowable(width="100%", thickness=2, color=NARANJA, spaceAfter=10))

    # ── Datos del cliente ─────────────────────────────────────────────────────
    elems.append(_seccion("DATOS DEL CLIENTE", es["seccion"]))
    elems.append(Spacer(1, 8))
    t = Table(
        [
            [Paragraph("CLIENTE", es["label"]), Paragraph("EMPRESA", es["label"]), Paragraph("TELÉFONO", es["label"])],
            [
                Paragraph(str(viaje.get("cliente") or "—"), es["valor"]),
                Paragraph(str(viaje.get("cliente_empresa") or "—"), es["valor"]),
                Paragraph(str(viaje.get("cliente_telefono") or "—"), es["valor"]),
            ],
        ],
        colWidths=[6 * cm, 6 * cm, 5 * cm],
    )
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2)]))
    elems.append(t)
    elems.append(Spacer(1, 12))

    # ── Trayecto ──────────────────────────────────────────────────────────────
    elems.append(_seccion("TRAYECTO", es["seccion"]))
    elems.append(Spacer(1, 8))
    t = Table(
        [
            [Paragraph("ORIGEN", es["label"]), Paragraph("DESTINO", es["label"])],
            [
                Paragraph(str(viaje.get("origen") or "—"), es["valor"]),
                Paragraph(str(viaje.get("destino") or "—"), es["valor"]),
            ],
        ],
        colWidths=[8.5 * cm, 8.5 * cm],
    )
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elems.append(t)
    elems.append(Spacer(1, 12))

    # ── Vehículo y conductor ──────────────────────────────────────────────────
    matricula = (
        viaje.get("vehiculo_placa")
        or viaje.get("vehiculo_matricula")
        or "—"
    )
    marca_modelo = " ".join(filter(None, [viaje.get("vehiculo_marca"), viaje.get("vehiculo_modelo")])) or "—"

    elems.append(_seccion("VEHÍCULO Y CONDUCTOR", es["seccion"]))
    elems.append(Spacer(1, 8))
    t = Table(
        [
            [
                Paragraph("CONDUCTOR", es["label"]),
                Paragraph("TELÉFONO", es["label"]),
                Paragraph("VEHÍCULO", es["label"]),
                Paragraph("MATRÍCULA", es["label"]),
            ],
            [
                Paragraph(str(viaje.get("camionero_nombre") or "—"), es["valor"]),
                Paragraph(str(viaje.get("camionero_telefono") or "—"), es["valor"]),
                Paragraph(marca_modelo, es["valor"]),
                Paragraph(str(matricula), es["valor"]),
            ],
        ],
        colWidths=[5 * cm, 4 * cm, 4.5 * cm, 3.5 * cm],
    )
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elems.append(t)
    elems.append(Spacer(1, 12))

    # ── Mercancía ─────────────────────────────────────────────────────────────
    elems.append(_seccion("MERCANCÍA", es["seccion"]))
    elems.append(Spacer(1, 8))
    t = Table(
        [
            [Paragraph("DESCRIPCIÓN DE LA MERCANCÍA", es["label"]), Paragraph("PESO / CAPACIDAD", es["label"])],
            [
                Paragraph(str(viaje.get("mercancia") or "—"), es["valor"]),
                Paragraph(str(viaje.get("peso") or "—"), es["valor"]),
            ],
        ],
        colWidths=[11 * cm, 6 * cm],
    )
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elems.append(t)
    elems.append(Spacer(1, 12))

    # ── Observaciones ─────────────────────────────────────────────────────────
    elems.append(_seccion("OBSERVACIONES", es["seccion"]))
    elems.append(Spacer(1, 8))
    obs_text = str(viaje.get("observaciones") or "Sin observaciones.")
    t = Table(
        [[Paragraph(obs_text, es["obs"])]],
        colWidths=[17 * cm],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GRIS_FONDO),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    elems.append(t)
    elems.append(Spacer(1, 20))

    # ── Firmas ────────────────────────────────────────────────────────────────
    elems.append(_seccion("FIRMAS Y CONFORMIDAD", es["seccion"]))
    elems.append(Spacer(1, 32))

    linea = "_" * 26
    t = Table(
        [
            [linea, linea, linea],
            [
                Paragraph("Empresa / Expedidor", es["firma_label"]),
                Paragraph("Conductor", es["firma_label"]),
                Paragraph("Cliente / Receptor", es["firma_label"]),
            ],
        ],
        colWidths=[5.5 * cm, 5.5 * cm, 5.5 * cm],
        hAlign="CENTER",
    )
    t.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("TEXTCOLOR", (0, 0), (-1, 0), GRIS_TEXTO),
    ]))
    elems.append(t)

    # ── Pie ───────────────────────────────────────────────────────────────────
    elems.append(Spacer(1, 20))
    elems.append(HRFlowable(width="100%", thickness=1, color=GRIS_FONDO, spaceAfter=6))
    elems.append(Paragraph(
        f"Documento generado por Mercatoria Truck · Orden N° {orden_id:04d}",
        es["pie"],
    ))

    doc.build(elems)
    buffer.seek(0)
    return buffer.read()
