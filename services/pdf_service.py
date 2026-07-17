import io
import os
from datetime import datetime

from database import conectar
from db_config import USE_POSTGRES


def ph():
    return "%s" if USE_POSTGRES else "?"

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
_LOGO_SVG_PATH = os.path.join(_BASE_DIR, "static", "logo-mercatoria.svg")


def _cargar_logo(width=2.2*cm, height=2.2*cm):
    if os.path.exists(_LOGO_PATH):
        return Image(_LOGO_PATH, width=width, height=height)
    try:
        from svglib.svglib import svg2rlg
        if os.path.exists(_LOGO_SVG_PATH):
            drawing = svg2rlg(_LOGO_SVG_PATH)
            if drawing:
                sx = width / drawing.width
                sy = height / drawing.height
                drawing.width = width
                drawing.height = height
                drawing.transform = (sx, 0, 0, sy, 0, 0)
                return drawing
    except ImportError:
        pass
    return ""

NARANJA = colors.HexColor("#E86A2C")
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
    logo_cell = _cargar_logo(width=5 * cm, height=2.5 * cm)

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

    # ── Datos de pago ─────────────────────────────────────────────────────────
    pago_camionero = viaje.get("pago_camionero")
    litros_combustible = viaje.get("litros_combustible")
    elems.append(_seccion("DATOS DE PAGO", es["seccion"]))
    elems.append(Spacer(1, 8))
    t = Table(
        [
            [Paragraph("PAGO AL TRANSPORTISTA", es["label"]), Paragraph("COMBUSTIBLE CONFIRMADO", es["label"])],
            [
                Paragraph(f"${pago_camionero:.2f}" if pago_camionero is not None else "—", es["valor"]),
                Paragraph(f"{litros_combustible:.1f} L" if litros_combustible else "Pendiente de confirmar", es["valor"]),
            ],
        ],
        colWidths=[8.5 * cm, 8.5 * cm],
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


def generar_pdf_liquidacion_camionero(viaje_id: int) -> bytes:
    from services.finanzas_service import calcular_liquidacion

    con = conectar()
    cur = con.cursor()
    cur.execute(f"""
        SELECT
            v.*,
            c.nombre   AS cam_nombre,
            c.telefono AS cam_telefono,
            c.licencia AS cam_licencia,
            r.nombre   AS ruta_nombre,
            r.km_oficiales
        FROM viajes v
        LEFT JOIN camioneros c ON v.camionero_id = c.id
        LEFT JOIN rutas      r ON v.ruta_id      = r.id
        WHERE v.id = {ph()}
    """, (viaje_id,))
    row = cur.fetchone()
    con.close()

    if not row:
        raise ValueError(f"Viaje #{viaje_id} no encontrado.")
    v = dict(row)
    if not v.get("camionero_id"):
        raise ValueError("El viaje no tiene transportista asignado.")

    liq = calcular_liquidacion(viaje_id)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2 * cm, leftMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )
    es = _estilos()
    elems = []

    fecha_emision = datetime.now().strftime("%d/%m/%Y")
    liq_num = v.get("id", 0)

    # ── Cabecera ──────────────────────────────────────────────────────────────
    logo_cell = _cargar_logo(width=5 * cm, height=2.5 * cm)

    right_col = Table(
        [
            [Paragraph("LIQUIDACION DE TRANSPORTISTA", es["titulo"])],
            [Paragraph(f"LIQ-{liq_num:04d}", es["numero"])],
            [Paragraph(f"Fecha de emision: {fecha_emision}", es["fecha"])],
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

    # ── Datos del transportista ────────────────────────────────────────────────
    elems.append(_seccion("DATOS DEL TRANSPORTISTA", es["seccion"]))
    elems.append(Spacer(1, 8))
    t = Table(
        [
            [Paragraph("NOMBRE", es["label"]), Paragraph("TELEFONO", es["label"]), Paragraph("LICENCIA", es["label"])],
            [
                Paragraph(str(v.get("cam_nombre") or "---"), es["valor"]),
                Paragraph(str(v.get("cam_telefono") or "---"), es["valor"]),
                Paragraph(str(v.get("cam_licencia") or "---"), es["valor"]),
            ],
        ],
        colWidths=[7 * cm, 5 * cm, 5 * cm],
    )
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2)]))
    elems.append(t)
    elems.append(Spacer(1, 12))

    # ── Detalle del viaje ─────────────────────────────────────────────────────
    elems.append(_seccion("DETALLE DEL VIAJE", es["seccion"]))
    elems.append(Spacer(1, 8))
    ruta_texto = v.get("ruta_nombre") or f"{v.get('origen') or '---'} > {v.get('destino') or '---'}"
    km_of = v.get("km_oficiales")
    km_of_texto = f"{int(km_of)} km" if km_of else "---"
    km_liq = liq["km_liquidable"] if liq else 0
    t = Table(
        [
            [Paragraph("RUTA", es["label"]), Paragraph("KM OFICIALES", es["label"]), Paragraph("KM LIQUIDABLES", es["label"])],
            [
                Paragraph(ruta_texto, es["valor"]),
                Paragraph(km_of_texto, es["valor"]),
                Paragraph(f"{int(km_liq)} km", es["valor"]),
            ],
        ],
        colWidths=[7 * cm, 5 * cm, 5 * cm],
    )
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elems.append(t)
    elems.append(Spacer(1, 12))

    # ── Resumen financiero ────────────────────────────────────────────────────
    elems.append(_seccion("RESUMEN FINANCIERO", es["seccion"]))
    elems.append(Spacer(1, 8))

    th = ParagraphStyle("LiqTH", parent=es["seccion"], leftIndent=0, fontSize=9,
                        fontName="Helvetica-Bold", textColor=colors.white)
    td = ParagraphStyle("LiqTD", parent=es["obs"], fontSize=11, textColor=GRIS_TEXTO)
    td_r = ParagraphStyle("LiqTDR", parent=td, alignment=TA_RIGHT)
    td_neg = ParagraphStyle("LiqTDNeg", parent=td_r, textColor=colors.HexColor("#c0392b"))
    td_total = ParagraphStyle("LiqTotal", parent=td_r, fontSize=13,
                              fontName="Helvetica-Bold", textColor=NARANJA)

    pago_base = liq["pago_camionero"] if liq else 0
    combustible = liq["combustible"] if liq else 0
    total_neto = pago_base - combustible

    tabla_data = [
        [Paragraph("CONCEPTO", th), Paragraph("MONTO (USD)", th)],
        [Paragraph("Pago base transportista", td), Paragraph(f"${pago_base:,.2f}", td_r)],
        [Paragraph("Combustible descontado", td), Paragraph(f"-${combustible:,.2f}", td_neg)],
        [Paragraph("TOTAL NETO A COBRAR", td), Paragraph(f"${total_neto:,.2f}", td_total)],
    ]
    tabla = Table(tabla_data, colWidths=[13 * cm, 4 * cm])
    tabla.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  NARANJA),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("LINEBELOW",     (0, 1), (-1, 2),  0.5, colors.HexColor("#dddddd")),
        ("BACKGROUND",    (0, 3), (-1, 3),  GRIS_FONDO),
        ("ALIGN",         (1, 0), (1, -1),  "RIGHT"),
    ]))
    elems.append(tabla)
    elems.append(Spacer(1, 10))

    if liq and liq.get("minimo_aplicado"):
        nota = Table(
            [[Paragraph(
                f"Km minimo garantizado aplicado ({int(liq['km_liquidable'])} km en lugar de {int(liq['km_real'])} km reales).",
                ParagraphStyle("Nota", parent=es["obs"], fontSize=10,
                               textColor=colors.HexColor("#7a5800")),
            )]],
            colWidths=[17 * cm],
        )
        nota.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#fff8e6")),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ]))
        elems.append(nota)
        elems.append(Spacer(1, 10))

    # ── Firmas ────────────────────────────────────────────────────────────────
    elems.append(_seccion("CONFORMIDAD Y FIRMA", es["seccion"]))
    elems.append(Spacer(1, 32))

    linea = "_" * 28
    firma_t = Table(
        [
            [linea, linea],
            [
                Paragraph(str(v.get("cam_nombre") or "Transportista"), es["firma_label"]),
                Paragraph("Mercatoria Truck", es["firma_label"]),
            ],
        ],
        colWidths=[8 * cm, 8 * cm],
        hAlign="CENTER",
    )
    firma_t.setStyle(TableStyle([
        ("ALIGN",     (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE",  (0, 0), (-1, 0),  10),
        ("TEXTCOLOR", (0, 0), (-1, 0),  GRIS_TEXTO),
    ]))
    elems.append(firma_t)

    # ── Pie ───────────────────────────────────────────────────────────────────
    elems.append(Spacer(1, 20))
    elems.append(HRFlowable(width="100%", thickness=1, color=GRIS_FONDO, spaceAfter=6))
    elems.append(Paragraph(
        f"Mercatoria Truck - Liquidacion LIQ-{liq_num:04d} - Emitida el {fecha_emision}",
        es["pie"],
    ))

    doc.build(elems)
    buffer.seek(0)
    return buffer.read()


def generar_pdf_carta_porte(viaje_id: int) -> bytes:
    con = conectar()
    cur = con.cursor()
    cur.execute(f"""
        SELECT
            v.*,
            c.nombre             AS cam_nombre,
            c.telefono           AS cam_telefono,
            c.licencia           AS cam_licencia,
            c.carnet_identidad   AS cam_carnet,
            c.licencia_operativa AS cam_licencia_op,
            c.empresa            AS cam_empresa,
            cl.nombre            AS cli_nombre,
            cl.telefono          AS cli_telefono,
            cl.empresa           AS cli_empresa,
            cl.email             AS cli_email,
            veh.marca            AS veh_marca,
            veh.modelo           AS veh_modelo,
            veh.matricula        AS veh_matricula,
            veh.tipo             AS veh_tipo,
            veh.chapa_remolque   AS veh_chapa,
            r.nombre             AS ruta_nombre,
            r.km_oficiales       AS ruta_km
        FROM viajes v
        LEFT JOIN camioneros c   ON v.camionero_id = c.id
        LEFT JOIN clientes   cl  ON v.cliente_id   = cl.id
        LEFT JOIN vehiculos  veh ON v.vehiculo_id  = veh.id
        LEFT JOIN rutas      r   ON v.ruta_id      = r.id
        WHERE v.id = {ph()}
    """, (viaje_id,))
    row = cur.fetchone()
    con.close()

    if not row:
        raise ValueError(f"Viaje #{viaje_id} no encontrado.")
    v = dict(row)
    if not v.get("camionero_id"):
        raise ValueError("El viaje no tiene transportista asignado.")
    if not v.get("vehiculo_id"):
        raise ValueError("El viaje no tiene vehículo asignado.")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2 * cm, leftMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )
    es = _estilos()
    elems = []

    cp_num = v.get("id", 0)
    fecha_emision = datetime.now().strftime("%d/%m/%Y")

    # ── Cabecera ──────────────────────────────────────────────────────────────
    logo_cell = _cargar_logo(width=5 * cm, height=2.5 * cm)

    right_col = Table(
        [
            [Paragraph("CARTA DE PORTE", es["titulo"])],
            [Paragraph(f"CP-{cp_num:04d}", es["numero"])],
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

    # ── Datos del remitente ───────────────────────────────────────────────────
    elems.append(_seccion("DATOS DEL REMITENTE", es["seccion"]))
    elems.append(Spacer(1, 8))

    nombre_cli   = v.get("cli_nombre")   or v.get("cliente") or "—"
    empresa_cli  = v.get("cli_empresa")  or "—"
    telefono_cli = v.get("cli_telefono") or "—"
    email_cli    = v.get("cli_email")    or "—"

    t = Table(
        [
            [Paragraph("NOMBRE", es["label"]),     Paragraph("EMPRESA", es["label"]),
             Paragraph("TELÉFONO", es["label"]),   Paragraph("EMAIL", es["label"])],
            [Paragraph(nombre_cli,   es["valor"]), Paragraph(empresa_cli,  es["valor"]),
             Paragraph(telefono_cli, es["valor"]), Paragraph(email_cli,    es["valor"])],
        ],
        colWidths=[4 * cm, 4.5 * cm, 3.5 * cm, 5 * cm],
    )
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2)]))
    elems.append(t)
    elems.append(Spacer(1, 12))

    # ── Datos del transporte ──────────────────────────────────────────────────
    elems.append(_seccion("DATOS DEL TRANSPORTISTA", es["seccion"]))
    elems.append(Spacer(1, 8))

    marca_modelo = " ".join(filter(None, [v.get("veh_marca"), v.get("veh_modelo")])) or "—"

    # Fila 1: nombre, carnet, matrícula, chapa remolque
    t1 = Table(
        [
            [Paragraph("CONDUCTOR",       es["label"]),
             Paragraph("CARNET / DUI",    es["label"]),
             Paragraph("MATRÍCULA",       es["label"]),
             Paragraph("CHAPA REMOLQUE",  es["label"])],
            [Paragraph(str(v.get("cam_nombre")    or "—"), es["valor"]),
             Paragraph(str(v.get("cam_carnet")    or "—"), es["valor"]),
             Paragraph(str(v.get("veh_matricula") or "—"), es["valor"]),
             Paragraph(str(v.get("veh_chapa")     or "—"), es["valor"])],
        ],
        colWidths=[5.5 * cm, 4 * cm, 3.5 * cm, 4 * cm],
    )
    t1.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2)]))
    elems.append(t1)
    elems.append(Spacer(1, 6))

    # Fila 2: licencia, licencia operativa, empresa, vehículo, tipo
    t2 = Table(
        [
            [Paragraph("LICENCIA",          es["label"]),
             Paragraph("LIC. OPERATIVA",    es["label"]),
             Paragraph("EMPRESA",           es["label"]),
             Paragraph("VEHÍCULO",          es["label"]),
             Paragraph("TIPO",              es["label"])],
            [Paragraph(str(v.get("cam_licencia")    or "—"), es["valor"]),
             Paragraph(str(v.get("cam_licencia_op") or "—"), es["valor"]),
             Paragraph(str(v.get("cam_empresa")     or "—"), es["valor"]),
             Paragraph(marca_modelo,                          es["valor"]),
             Paragraph(str(v.get("veh_tipo")        or "—"), es["valor"])],
        ],
        colWidths=[3 * cm, 3 * cm, 4 * cm, 4 * cm, 3 * cm],
    )
    t2.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2)]))
    elems.append(t2)
    elems.append(Spacer(1, 12))

    # ── Descripción de la carga ───────────────────────────────────────────────
    elems.append(_seccion("DESCRIPCIÓN DE LA CARGA", es["seccion"]))
    elems.append(Spacer(1, 8))

    obs_raw = str(v.get("observaciones") or "")
    tipo_carga = peso = notas = ""
    for linea in obs_raw.splitlines():
        low = linea.lower()
        if "tipo" in low and not tipo_carga:
            tipo_carga = linea.split(":", 1)[-1].strip()
        elif "peso" in low and not peso:
            peso = linea.split(":", 1)[-1].strip()
        elif linea.strip():
            notas += linea.strip() + " "
    if not tipo_carga and not peso:
        notas = obs_raw or "Sin descripción."

    t = Table(
        [
            [Paragraph("TIPO DE CARGA", es["label"]), Paragraph("PESO APROXIMADO", es["label"])],
            [Paragraph(tipo_carga or "—",             es["valor"]), Paragraph(peso or "—", es["valor"])],
        ],
        colWidths=[8.5 * cm, 8.5 * cm],
    )
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elems.append(t)
    elems.append(Spacer(1, 6))

    t_notas = Table(
        [[Paragraph(notas.strip() or "Sin notas adicionales.", es["obs"])]],
        colWidths=[17 * cm],
    )
    t_notas.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), GRIS_FONDO),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    elems.append(t_notas)
    elems.append(Spacer(1, 12))

    # ── Ruta ──────────────────────────────────────────────────────────────────
    elems.append(_seccion("RUTA", es["seccion"]))
    elems.append(Spacer(1, 8))

    km_texto = f"{int(v['ruta_km'])} km" if v.get("ruta_km") else "—"
    ruta_nombre = v.get("ruta_nombre") or "—"

    t = Table(
        [
            [Paragraph("ORIGEN",       es["label"]), Paragraph("DESTINO",    es["label"]),
             Paragraph("KM OFICIALES", es["label"]), Paragraph("NOMBRE RUTA", es["label"])],
            [Paragraph(str(v.get("origen")  or "—"), es["valor"]),
             Paragraph(str(v.get("destino") or "—"), es["valor"]),
             Paragraph(km_texto,                      es["valor"]),
             Paragraph(ruta_nombre,                   es["valor"])],
        ],
        colWidths=[4.5 * cm, 4.5 * cm, 3 * cm, 5 * cm],
    )
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elems.append(t)
    elems.append(Spacer(1, 12))

    # ── Condiciones ───────────────────────────────────────────────────────────
    elems.append(_seccion("CONDICIONES DE TRANSPORTE", es["seccion"]))
    elems.append(Spacer(1, 8))

    estilo_cond = ParagraphStyle(
        "Cond", parent=es["obs"],
        fontSize=10, textColor=GRIS_TEXTO, leading=16,
    )
    t_cond = Table(
        [[Paragraph(
            "La mercancía viaja bajo responsabilidad del transportista desde la recogida hasta "
            "la entrega. Mercatoria Truck actúa como intermediario logístico.",
            estilo_cond,
        )]],
        colWidths=[17 * cm],
    )
    t_cond.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), GRIS_FONDO),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
    ]))
    elems.append(t_cond)
    elems.append(Spacer(1, 20))

    # ── Firmas ────────────────────────────────────────────────────────────────
    elems.append(_seccion("FIRMAS", es["seccion"]))
    elems.append(Spacer(1, 32))

    linea = "_" * 26
    firma_t = Table(
        [
            [linea, linea, linea],
            [
                Paragraph("Remitente", es["firma_label"]),
                Paragraph("Transportista", es["firma_label"]),
                Paragraph("Receptor", es["firma_label"]),
            ],
        ],
        colWidths=[5.5 * cm, 5.5 * cm, 5.5 * cm],
        hAlign="CENTER",
    )
    firma_t.setStyle(TableStyle([
        ("ALIGN",     (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE",  (0, 0), (-1, 0),  10),
        ("TEXTCOLOR", (0, 0), (-1, 0),  GRIS_TEXTO),
    ]))
    elems.append(firma_t)

    # ── Pie ───────────────────────────────────────────────────────────────────
    elems.append(Spacer(1, 20))
    elems.append(HRFlowable(width="100%", thickness=1, color=GRIS_FONDO, spaceAfter=6))
    elems.append(Paragraph(
        f"Mercatoria Truck · Carta de Porte N° CP-{cp_num:04d} · Emitida el {fecha_emision}",
        es["pie"],
    ))

    doc.build(elems)
    buffer.seek(0)
    return buffer.read()


def generar_factura_cliente(viaje_id: int) -> bytes:
    con = conectar()
    cur = con.cursor()
    cur.execute(f"""
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
        WHERE v.id = {ph()}
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

    nombre_check = v.get("cli_nombre") or ""
    if not nombre_check.strip() or "@" in nombre_check:
        raise ValueError("El cliente no tiene nombre real registrado. Ve a Clientes, edita el registro y agrega el nombre antes de generar la factura.")

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
    logo_cell = _cargar_logo(width=5 * cm, height=2.5 * cm)

    right_col = Table(
        [
            [Paragraph("FACTURA", es["titulo"])],
            [Paragraph(f"MT-{factura_num:04d}", es["numero"])],
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

    if empresa_cli and empresa_cli != "—":
        t = Table(
            [
                [Paragraph("NOMBRE", estilo_label_fac),    Paragraph("EMPRESA", estilo_label_fac),
                 Paragraph("EMAIL", estilo_label_fac),      Paragraph("TELÉFONO", estilo_label_fac)],
                [Paragraph(nombre_cli,   estilo_valor_fac), Paragraph(empresa_cli,  estilo_valor_fac),
                 Paragraph(email_cli,    estilo_valor_fac), Paragraph(telefono_cli, estilo_valor_fac)],
            ],
            colWidths=[4.5 * cm, 4 * cm, 5 * cm, 3.5 * cm],
        )
    else:
        t = Table(
            [
                [Paragraph("NOMBRE", estilo_label_fac), Paragraph("EMAIL", estilo_label_fac),
                 Paragraph("TELÉFONO", estilo_label_fac)],
                [Paragraph(nombre_cli,   estilo_valor_fac),
                 Paragraph(email_cli,    estilo_valor_fac),
                 Paragraph(telefono_cli, estilo_valor_fac)],
            ],
            colWidths=[5.5 * cm, 6 * cm, 5.5 * cm],
        )
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2)]))
    elems.append(t)
    elems.append(Spacer(1, 12))

    # ── Detalle del servicio ──────────────────────────────────────────────────
    elems.append(_seccion("DETALLE DEL SERVICIO", estilo_seccion_fac))
    elems.append(Spacer(1, 8))

    ruta        = f"{v.get('origen') or '—'} → {v.get('destino') or '—'}"
    fecha_viaje = _formato_fecha(v.get("fecha_creacion"))

    t = Table(
        [
            [Paragraph("RUTA", estilo_label_fac), Paragraph("FECHA", estilo_label_fac)],
            [Paragraph(ruta,        estilo_valor_fac),
             Paragraph(fecha_viaje, estilo_valor_fac)],
        ],
        colWidths=[10 * cm, 7 * cm],
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
        ("BACKGROUND",    (0, 0), (-1, -1), NARANJA),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("ROUNDEDCORNERS", [6]),
    ]))
    elems.append(total_box)
    elems.append(Spacer(1, 12))

    # ── Condiciones de pago ───────────────────────────────────────────────────
    cond_text = (
        "• Pago acordado en USD (dólares americanos)<br/>"
        "• Este documento es válido como comprobante del servicio prestado<br/>"
        "• Emitido por MERCATORIA S.R.L. — mercatoria.us"
    )
    t_cond = Table(
        [[Paragraph(cond_text, estilo_condiciones)]],
        colWidths=[17 * cm],
    )
    t_cond.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), GRIS_FONDO),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
    ]))
    elems.append(t_cond)
    elems.append(Spacer(1, 14))

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
        f"Mercatoria Truck · Factura N° MT-{factura_num:04d} · Emitida el {fecha_emision}",
        es["pie"],
    ))

    doc.build(elems)
    buffer.seek(0)
    return buffer.read()
