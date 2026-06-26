import io
import os
import sqlite3
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


def generar_factura_cliente(viaje_id: int) -> bytes:
    db_path = os.path.join(_BASE_DIR, "mercatoria.db")
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("""
        SELECT
            v.*,
            cl.nombre    AS cli_nombre,
            cl.empresa   AS cli_empresa,
            cl.email     AS cli_email,
            cl.telefono  AS cli_telefono,
            tv.nombre    AS tipo_vehiculo_nombre
        FROM viajes v
        LEFT JOIN clientes      cl ON v.cliente_id      = cl.id
        LEFT JOIN tipos_vehiculo tv ON v.tipo_vehiculo_id = tv.id
        WHERE v.id = ?
    """, (viaje_id,))
    row = cur.fetchone()
    con.close()

    if not row:
        raise ValueError(f"Viaje #{viaje_id} no encontrado.")

    v = dict(row)

    if (v.get("estado") or "").lower() == "cancelado":
        raise ValueError("No se puede generar factura para un viaje cancelado.")

    if not v.get("cliente") and not v.get("cliente_id"):
        raise ValueError("El viaje no tiene cliente asignado.")

    precio = (
        float(v.get("precio_final") or 0)
        or float(v.get("precio_cliente") or 0)
        or float(v.get("precio") or 0)
    )
    if precio <= 0:
        raise ValueError("El viaje no tiene precio cliente confirmado.")

    return _construir_pdf_factura(v, precio)


def _construir_pdf_factura(v: dict, precio: float) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2 * cm, leftMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )
    es = _estilos()

    VERDE = colors.HexColor("#27ae60")

    estilo_label_fac = ParagraphStyle(
        "LabelFac", parent=es["label"],
        fontSize=8, textColor=colors.grey,
    )
    estilo_valor_fac = ParagraphStyle(
        "ValorFac", parent=es["valor"],
        fontSize=11, fontName="Helvetica-Bold", textColor=GRIS_TEXTO,
    )
    estilo_seccion_fac = ParagraphStyle(
        "SeccionFac", parent=es["seccion"],
        fontSize=9, fontName="Helvetica-Bold", textColor=colors.white,
        leftIndent=8,
    )
    estilo_total_label = ParagraphStyle(
        "TotalLabel", parent=es["label"],
        fontSize=10, fontName="Helvetica-Bold",
        textColor=colors.white, alignment=TA_CENTER,
    )
    estilo_total_valor = ParagraphStyle(
        "TotalValor", parent=es["valor"],
        fontSize=18, fontName="Helvetica-Bold",
        textColor=colors.white, alignment=TA_CENTER,
    )
    estilo_condiciones = ParagraphStyle(
        "Condiciones", parent=es["obs"],
        fontSize=10, textColor=GRIS_TEXTO, leading=16,
    )

    elems = []
    factura_num = v.get("id", 0)
    fecha_emision = datetime.now().strftime("%d/%m/%Y")

    # ── Cabecera ──────────────────────────────────────────────────────────────
    logo_cell = ""
    if os.path.exists(_LOGO_PATH):
        logo_cell = Image(_LOGO_PATH, width=5 * cm, height=2.5 * cm, kind="proportional")

    right_col = Table(
        [
            [Paragraph("FACTURA", es["titulo"])],
            [Paragraph(f"FAC-{factura_num:04d}", es["numero"])],
            [Paragraph(f"Fecha de emisión: {fecha_emision}", es["fecha"])],
        ],
        colWidths=[8 * cm],
    )
    right_col.setStyle(TableStyle([
        ("ALIGN",         (0, 0), (-1, -1), "RIGHT"),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
    ]))
    cabecera = Table([[logo_cell, right_col]], colWidths=[9 * cm, 8 * cm])
    cabecera.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elems.append(cabecera)
    elems.append(HRFlowable(width="100%", thickness=2, color=NARANJA, spaceAfter=10))

    # ── Datos del cliente ─────────────────────────────────────────────────────
    elems.append(_seccion("DATOS DEL CLIENTE", estilo_seccion_fac))
    elems.append(Spacer(1, 8))

    nombre_cli   = v.get("cli_nombre")   or v.get("cliente") or "—"
    empresa_cli  = v.get("cli_empresa")  or "—"
    email_cli    = v.get("cli_email")    or "—"
    telefono_cli = v.get("cli_telefono") or "—"

    t = Table(
        [
            [Paragraph("NOMBRE", estilo_label_fac),       Paragraph("EMPRESA", estilo_label_fac),
             Paragraph("EMAIL", estilo_label_fac),         Paragraph("TELÉFONO", estilo_label_fac)],
            [Paragraph(nombre_cli,   estilo_valor_fac),    Paragraph(empresa_cli,  estilo_valor_fac),
             Paragraph(email_cli,    estilo_valor_fac),    Paragraph(telefono_cli, estilo_valor_fac)],
        ],
        colWidths=[4.5 * cm, 4 * cm, 5 * cm, 3.5 * cm],
    )
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2)]))
    elems.append(t)
    elems.append(Spacer(1, 12))

    # ── Detalle del servicio ──────────────────────────────────────────────────
    elems.append(_seccion("DETALLE DEL SERVICIO", estilo_seccion_fac))
    elems.append(Spacer(1, 8))

    ruta        = f"{v.get('origen') or '—'} → {v.get('destino') or '—'}"
    fecha_viaje = _formato_fecha(v.get("fecha_creacion"))
    tipo_carga  = v.get("tipo_vehiculo_nombre") or v.get("mercancia") or "—"

    t = Table(
        [
            [Paragraph("RUTA", estilo_label_fac),  Paragraph("FECHA DEL VIAJE", estilo_label_fac),
             Paragraph("TIPO DE CARGA", estilo_label_fac)],
            [Paragraph(ruta,         estilo_valor_fac),
             Paragraph(fecha_viaje,  estilo_valor_fac),
             Paragraph(tipo_carga,   estilo_valor_fac)],
        ],
        colWidths=[7 * cm, 4.5 * cm, 5.5 * cm],
    )
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elems.append(t)
    elems.append(Spacer(1, 14))

    # ── Tabla de conceptos ────────────────────────────────────────────────────
    elems.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#dddddd"), spaceAfter=6))

    th_style = ParagraphStyle("TH", parent=es["seccion"], leftIndent=0, fontSize=9,
                               fontName="Helvetica-Bold", textColor=colors.white)
    td_style = ParagraphStyle("TD", parent=es["obs"], fontSize=10, textColor=GRIS_TEXTO)
    td_r     = ParagraphStyle("TDR", parent=td_style, alignment=TA_RIGHT)

    concepto_texto = f"Servicio de transporte: {v.get('origen') or ''} → {v.get('destino') or ''}"
    tabla_data = [
        [Paragraph("CONCEPTO", th_style), Paragraph("MONTO (USD)", th_style)],
        [Paragraph(concepto_texto, td_style), Paragraph(f"${precio:,.2f}", td_r)],
        [Paragraph("SUBTOTAL", td_style), Paragraph(f"${precio:,.2f}", td_r)],
    ]
    tabla = Table(tabla_data, colWidths=[13 * cm, 4 * cm])
    tabla.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  NARANJA),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("LINEBELOW",     (0, 1), (-1, 1),  0.5, colors.HexColor("#dddddd")),
        ("BACKGROUND",    (0, 2), (-1, 2),  GRIS_FONDO),
        ("ALIGN",         (1, 0), (1, -1),  "RIGHT"),
    ]))
    elems.append(tabla)
    elems.append(Spacer(1, 10))

    # ── Caja total ────────────────────────────────────────────────────────────
    total_box = Table(
        [
            [Paragraph("TOTAL A PAGAR", estilo_total_label)],
            [Paragraph(f"USD ${precio:,.2f}", estilo_total_valor)],
        ],
        colWidths=[17 * cm],
    )
    total_box.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), VERDE),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("ROUNDEDCORNERS", [6]),
    ]))
    elems.append(total_box)
    elems.append(Spacer(1, 14))

    # ── Condiciones de pago ───────────────────────────────────────────────────
    elems.append(_seccion("CONDICIONES DE PAGO", estilo_seccion_fac))
    elems.append(Spacer(1, 8))
    condiciones_txt = (
        "• Pago neto a 30 días de la fecha de emisión de esta factura.<br/>"
        "• Formas de pago aceptadas: transferencia bancaria o efectivo.<br/>"
        "• En caso de mora se aplicará un recargo del 2% mensual sobre el saldo pendiente.<br/>"
        "• Esta factura es válida como comprobante de servicio prestado."
    )
    cond_table = Table([[Paragraph(condiciones_txt, estilo_condiciones)]], colWidths=[17 * cm])
    cond_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), GRIS_FONDO),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
    ]))
    elems.append(cond_table)
    elems.append(Spacer(1, 20))

    # ── Firmas ────────────────────────────────────────────────────────────────
    elems.append(_seccion("CONFORMIDAD Y FIRMA", estilo_seccion_fac))
    elems.append(Spacer(1, 30))

    linea = "_" * 28
    firma_t = Table(
        [
            [linea, linea],
            [
                Paragraph("Mercatoria Truck / Emisor", es["firma_label"]),
                Paragraph(f"{nombre_cli} / Receptor", es["firma_label"]),
            ],
        ],
        colWidths=[8 * cm, 8 * cm],
        hAlign="CENTER",
    )
    firma_t.setStyle(TableStyle([
        ("ALIGN",    (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, 0),  10),
        ("TEXTCOLOR",(0, 0), (-1, 0),  GRIS_TEXTO),
    ]))
    elems.append(firma_t)

    # ── Pie ───────────────────────────────────────────────────────────────────
    elems.append(Spacer(1, 20))
    elems.append(HRFlowable(width="100%", thickness=1, color=GRIS_FONDO, spaceAfter=6))
    elems.append(Paragraph(
        f"Mercatoria Truck · Factura N° FAC-{factura_num:04d} · Emitida el {fecha_emision}",
        es["pie"],
    ))

    doc.build(elems)
    buffer.seek(0)
    return buffer.read()
