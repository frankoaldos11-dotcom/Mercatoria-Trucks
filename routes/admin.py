import csv
import io
import json
import threading
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from datetime import date, datetime
from urllib.parse import quote_plus

from flask import Blueprint, render_template, request, redirect, send_file, session, jsonify

from database import conectar
from extensions import bcrypt, mail
from flask_mail import Message
from services.comercial_service import convertir_cotizacion_en_viaje, get_rutas_por_camionero
from services.finanzas_service import calcular_liquidacion
from services.pdf_service import generar_factura_cliente, generar_pdf_orden_carga
from utils.constants import CAMIONERO_ESTADOS, VEHICULO_ESTADOS

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def registrar_auditoria(accion, categoria, entidad=None, entidad_id=None, detalle=None):
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT INTO auditoria (usuario, rol, accion, categoria, entidad, entidad_id, detalle)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session.get("usuario", "sistema"),
            session.get("rol", ""),
            accion, categoria, entidad, entidad_id, detalle
        ))
        conexion.commit()
        conexion.close()
        print(f"AUDITORIA OK: {accion} | {categoria} | {entidad} #{entidad_id}")
    except Exception as e:
        print(f"AUDITORIA ERROR: {e}")


def notificar_cliente_estado(viaje_id, nuevo_estado, email_cliente):
    if not email_cliente or "@" not in email_cliente:
        return
    try:
        from flask import current_app
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT clave, valor FROM configuracion_texto")
        txt = {r["clave"]: r["valor"] for r in cursor.fetchall()}
        conexion.close()
        if txt.get("mail_username"):
            current_app.config["MAIL_USERNAME"] = txt["mail_username"]
        if txt.get("mail_password"):
            current_app.config["MAIL_PASSWORD"] = txt["mail_password"]

        emojis = {
            "Asignado": "🚛", "En ruta": "📍", "Entregado": "✅",
            "Cancelado": "❌", "Carga recogida": "📦",
        }
        emoji = emojis.get(nuevo_estado, "📋")
        msg = Message(
            subject=f"{emoji} Tu envío #{viaje_id} está: {nuevo_estado} — Mercatoria Truck",
            recipients=[email_cliente],
        )
        msg.body = (
            f"Hola,\n\n"
            f"Tu envío #{viaje_id} ha cambiado de estado.\n\n"
            f"Estado actual: {nuevo_estado}\n\n"
            f"Puedes ver el detalle completo en tu portal:\n"
            f"https://mercatoria-trucks.onrender.com/cliente/viajes/{viaje_id}\n\n"
            f"— Mercatoria Truck\n"
        )
        mail.send(msg)
    except Exception as e:
        print(f"Error enviando email: {e}")


def requiere_admin():
    return "usuario" in session and session.get("rol") in ["admin", "operador"]


@admin_bp.route("/")
def dashboard():
    if not requiere_admin():
        return redirect("/login")

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("SELECT COUNT(*) AS total FROM viajes WHERE LOWER(estado) IN ('pendiente', 'solicitado')")
    pendientes = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM viajes WHERE LOWER(estado) IN ('en ruta', 'en_ruta')")
    en_curso = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM viajes WHERE LOWER(estado) = 'entregado'")
    entregados = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM viajes WHERE LOWER(estado) = 'asignado'")
    asignados = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM viajes WHERE LOWER(estado) = 'cancelado'")
    cancelados = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM camioneros")
    camioneros = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM clientes")
    clientes = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT id, cliente, origen, destino, estado
        FROM viajes
        WHERE LOWER(estado) IN ('pendiente', 'solicitado')
        ORDER BY id DESC
    """)
    lista = cursor.fetchall()

    # Ingresos del mes actual
    cursor.execute("""
        SELECT COALESCE(SUM(COALESCE(precio_final, precio_cliente, precio, 0)), 0) AS total
        FROM viajes
        WHERE TO_CHAR(fecha_creacion, 'YYYY-MM') = TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM')
          AND LOWER(estado) != 'cancelado'
    """)
    ingresos_mes = round(cursor.fetchone()["total"], 2)

    # Camionero más activo (viajes totales)
    cursor.execute("""
        SELECT camionero_nombre, COUNT(*) as total
        FROM viajes
        WHERE camionero_nombre IS NOT NULL AND camionero_nombre != ''
          AND LOWER(estado) != 'cancelado'
        GROUP BY camionero_nombre
        ORDER BY total DESC LIMIT 1
    """)
    row = cursor.fetchone()
    camionero_top = row["camionero_nombre"] if row else "—"

    # Clientes sin nombre (para aviso)
    cursor.execute("""
        SELECT COUNT(*) AS total FROM clientes
        WHERE nombre IS NULL OR TRIM(nombre) = ''
    """)
    clientes_sin_nombre = cursor.fetchone()["total"]

    conexion.close()

    return render_template(
        "admin/dashboard.html",
        pendientes=pendientes,
        en_curso=en_curso,
        entregados=entregados,
        asignados=asignados,
        cancelados=cancelados,
        camioneros=camioneros,
        clientes=clientes,
        lista=lista,
        ingresos_mes=ingresos_mes,
        camionero_top=camionero_top,
        clientes_sin_nombre=clientes_sin_nombre
    )


@admin_bp.route("/viajes")
def viajes():
    if not requiere_admin():
        return redirect("/login")

    filtro = request.args.get("estado", "").strip().lower()
    buscar = request.args.get("buscar", "").strip()
    pagina = max(1, int(request.args.get("pagina", 1) or 1))
    por_pagina = 20

    condiciones = []
    params = []

    if filtro:
        condiciones.append("LOWER(v.estado) = ?")
        params.append(filtro)

    if buscar:
        condiciones.append("""(
            COALESCE(v.cliente, '') LIKE ?
            OR COALESCE(v.origen, '') LIKE ?
            OR COALESCE(v.destino, '') LIKE ?
            OR COALESCE(v.camionero_nombre, '') LIKE ?
        )""")
        like = f"%{buscar}%"
        params.extend([like, like, like, like])

    where = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute(f"""
        SELECT COUNT(*) AS total FROM viajes v
        {where}
    """, params)
    total = cursor.fetchone()["total"]

    total_paginas = max(1, (total + por_pagina - 1) // por_pagina)
    pagina = min(pagina, total_paginas)
    offset = (pagina - 1) * por_pagina

    cursor.execute(f"""
        SELECT v.id,
               COALESCE(v.cliente, 'Sin nombre') as cliente,
               v.origen, v.destino, v.estado, v.camionero_nombre,
               COALESCE(v.precio_final, v.precio_cliente, v.precio, 0) as precio,
               v.fecha_creacion
        FROM viajes v
        {where}
        ORDER BY v.id DESC
        LIMIT ? OFFSET ?
    """, params + [por_pagina, offset])
    lista = cursor.fetchall()
    print(f"DEBUG VIAJES: total={total}, lista_len={len(lista)}, where={where}, params={params}", flush=True)

    conexion.close()

    return render_template(
        "admin/viajes.html",
        lista=lista,
        filtro=filtro,
        buscar=buscar,
        pagina_actual=pagina,
        total_paginas=total_paginas,
        total=total,
    )


def _parsear_observaciones(obs):
    """Extrae tipo_carga, peso y notas del texto de observaciones."""
    resultado = {"tipo_carga": "", "peso": "", "notas": "", "crudo": obs or ""}
    if not obs:
        return resultado
    for linea in obs.split("\n"):
        linea = linea.strip()
        if linea.startswith("Tipo de carga:"):
            partes = linea.split("|")
            resultado["tipo_carga"] = partes[0].replace("Tipo de carga:", "").strip()
            if len(partes) > 1:
                resultado["peso"] = partes[1].replace("Peso aprox.:", "").strip()
        elif linea.startswith("Notas:"):
            resultado["notas"] = linea.replace("Notas:", "").strip()
    return resultado


@admin_bp.route("/viaje/<int:id>")
@admin_bp.route("/viajes/<int:id>/gestionar")
def gestionar_viaje(id):
    if not requiere_admin():
        return redirect("/login")

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT v.*,
               v.camionero_id as camionero_id
        FROM viajes v
        WHERE v.id = ?
    """, (id,))
    viaje = cursor.fetchone()

    if not viaje:
        conexion.close()
        return redirect("/admin/viajes")

    cursor.execute("""
        SELECT id, nombre, telefono, estado
        FROM camioneros
        WHERE activo = 1 OR activo IS NULL
        ORDER BY nombre
    """)
    camioneros = cursor.fetchall()
    vehiculos = []

    tipo_vehiculo_nombre = None
    if viaje["tipo_vehiculo_id"]:
        cursor.execute("SELECT nombre FROM tipos_vehiculo WHERE id = ?", (viaje["tipo_vehiculo_id"],))
        row = cursor.fetchone()
        tipo_vehiculo_nombre = row["nombre"] if row else None

    tarifa_info = None
    if viaje["tarifa_id"]:
        cursor.execute("""
            SELECT t.precio_cliente, tv.nombre AS tipo_nombre
            FROM tarifas t
            LEFT JOIN tipos_vehiculo tv ON t.tipo_vehiculo_id = tv.id
            WHERE t.id = ?
        """, (viaje["tarifa_id"],))
        row = cursor.fetchone()
        if row:
            tarifa_info = f"#{viaje['tarifa_id']} — {row['tipo_nombre'] or 'N/A'} · ${row['precio_cliente']:.2f}/km"

    # Datos enriquecidos del cliente
    cliente_info = None
    if viaje["cliente_id"]:
        cursor.execute(
            "SELECT nombre, telefono, empresa, email FROM clientes WHERE id = ?",
            (viaje["cliente_id"],)
        )
        cliente_info = cursor.fetchone()

    # Nombre legible de la ruta
    ruta_display = None
    if viaje["ruta_id"]:
        cursor.execute("SELECT origen, destino FROM rutas WHERE id = ?", (viaje["ruta_id"],))
        ruta_row = cursor.fetchone()
        if ruta_row:
            ruta_display = f"{ruta_row['origen']} → {ruta_row['destino']}"

    conexion.close()

    liquidacion = calcular_liquidacion(id)
    error = request.args.get("error")
    obs_parsed = _parsear_observaciones(viaje["observaciones"])

    _transiciones = {
        "solicitado":         ["Asignado", "En ruta", "Carga recogida", "Entregado", "Cancelado"],
        "pendiente":          ["Asignado", "En ruta", "Carga recogida", "Entregado", "Cancelado"],
        "asignado":           ["En ruta", "Carga recogida", "Entregado", "Cancelado"],
        "en ruta":            ["Carga recogida", "Entregado", "Asignado", "Cancelado"],
        "en_ruta":            ["Carga recogida", "Entregado", "Asignado", "Cancelado"],
        "carga recogida":     ["En ruta", "Entregado", "Cancelado"],
        "pendiente de pago":  ["Confirmado", "Entregado", "Cancelado"],
        "confirmado":         ["En ruta", "Carga recogida", "Entregado", "Cancelado"],
        "entregado":          ["En ruta", "Asignado", "Cancelado"],
        "cancelado":          ["Solicitado", "Asignado"],
    }
    estado_norm = (viaje["estado"] or "").lower()
    estados_validos = _transiciones.get(estado_norm, ["Asignado", "En ruta", "Entregado", "Cancelado"])

    orden_faltantes = []
    if not viaje["cliente"]:
        orden_faltantes.append("cliente")
    if not viaje["camionero_nombre"] and not viaje["camionero_id"]:
        orden_faltantes.append("camionero")
    if not viaje["vehiculo_id"]:
        orden_faltantes.append("vehículo")
    if not viaje["origen"]:
        orden_faltantes.append("origen")
    if not viaje["destino"]:
        orden_faltantes.append("destino")
    orden_carga_ok = len(orden_faltantes) == 0
    orden_carga_tooltip = "Falta: " + ", ".join(orden_faltantes) if orden_faltantes else ""

    conexion2 = conectar()
    cursor2 = conexion2.cursor()
    cursor2.execute("""
        SELECT usuario, texto, fecha
        FROM notas_viaje
        WHERE viaje_id = ?
        ORDER BY fecha DESC
    """, (id,))
    notas = cursor2.fetchall()
    conexion2.close()

    return render_template(
        "admin/gestionar_viaje.html",
        viaje=viaje,
        camioneros=camioneros,
        vehiculos=vehiculos,
        liquidacion=liquidacion,
        tipo_vehiculo_nombre=tipo_vehiculo_nombre,
        tarifa_info=tarifa_info,
        error=error,
        estados_validos=estados_validos,
        orden_carga_ok=orden_carga_ok,
        orden_carga_tooltip=orden_carga_tooltip,
        cliente_info=cliente_info,
        ruta_display=ruta_display,
        obs_parsed=obs_parsed,
        notas=notas,
    )


@admin_bp.route("/viaje/<int:id>/asignar", methods=["POST"])
def asignar_camionero(id):
    if not requiere_admin():
        return redirect("/login")

    camionero_id = request.form["camionero"]

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("SELECT nombre FROM camioneros WHERE id = ?", (camionero_id,))
    fila = cursor.fetchone()

    if fila:
        cursor.execute("""
            UPDATE viajes
            SET camionero_id = ?, camionero_nombre = ?, estado = 'Asignado'
            WHERE id = ?
        """, (camionero_id, fila["nombre"], id))

    conexion.commit()

    nombre_camionero = fila['nombre'] if fila else "desconocido"

    conexion.close()

    print(f"=== ANTES AUDITORIA: usuario={session.get('usuario')} rol={session.get('rol')} ===")
    registrar_auditoria(f"Asignó camionero {nombre_camionero}", "Viajes", "viaje", id, f"Camionero ID: {camionero_id}")
    print(f"=== DESPUES AUDITORIA ===")

    return redirect(f"/admin/viajes/{id}/gestionar")


@admin_bp.route("/viaje/<int:id>/estado", methods=["POST"])
def cambiar_estado(id):
    if not requiere_admin():
        return redirect("/login")

    estado = request.form["estado"]

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT camionero_id, vehiculo_id, precio_final, precio_cliente, precio, estado, cliente_id
        FROM viajes WHERE id = ?
    """, (id,))
    viaje = cursor.fetchone()

    if estado == "Asignado":
        if not viaje or not viaje["camionero_id"] or not viaje["vehiculo_id"]:
            conexion.close()
            return redirect(f"/admin/viajes/{id}/gestionar?error=Para+pasar+a+Asignado+debes+asignar+un+camionero+y+un+veh%C3%ADculo")

    cursor.execute("UPDATE viajes SET estado = ? WHERE id = ?", (estado, id))

    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if estado == "Asignado":
        cursor.execute("UPDATE viajes SET fecha_asignacion = ? WHERE id = ?", (ahora, id))
    elif estado in ["En ruta", "Carga recogida"]:
        cursor.execute("UPDATE viajes SET fecha_recogida = ? WHERE id = ?", (ahora, id))
    elif estado == "Entregado":
        cursor.execute("UPDATE viajes SET fecha_entrega = ? WHERE id = ?", (ahora, id))

    if estado.lower() in ["entregado", "cancelado"]:
        if viaje and viaje["vehiculo_id"]:
            cursor.execute(
                "UPDATE vehiculos SET estado = 'Disponible' WHERE id = ?",
                (viaje["vehiculo_id"],)
            )

    email_cliente = None
    if viaje and viaje["cliente_id"]:
        cursor.execute("SELECT email FROM clientes WHERE id = ?", (viaje["cliente_id"],))
        cli = cursor.fetchone()
        email_cliente = cli["email"] if cli else None

    estado_anterior = viaje["estado"] if viaje else None

    conexion.commit()
    conexion.close()

    if estado in ["Asignado", "En ruta", "Carga recogida", "Entregado", "Cancelado"]:
        notificar_cliente_estado(id, estado, email_cliente)

    registrar_auditoria(
        f"Cambió estado a {estado}", "Viajes", "viaje", id,
        f"Estado anterior: {estado_anterior}"
    )

    return redirect(f"/admin/viajes/{id}/gestionar")


@admin_bp.route("/viaje/<int:id>/asignar-vehiculo", methods=["POST"])
def asignar_vehiculo(id):
    if not requiere_admin():
        return redirect("/login")

    vehiculo_id = request.form["vehiculo"]

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("SELECT * FROM viajes WHERE id = ?", (id,))
    viaje = cursor.fetchone()

    if not viaje:
        conexion.close()
        return redirect("/admin/viajes")

    cursor.execute("""
        SELECT v.id, v.matricula, v.tipo_vehiculo_id, v.tipo, v.estado
        FROM vehiculos v
        WHERE
            v.id = ?
            AND v.activo = 1
            AND LOWER(v.estado) = 'disponible'
            AND (
                v.tipo_vehiculo_id = ?
                OR v.tipo = (SELECT nombre FROM tipos_vehiculo WHERE id = ?)
            )
    """, (vehiculo_id, viaje["tipo_vehiculo_id"], viaje["tipo_vehiculo_id"]))
    vehiculo = cursor.fetchone()

    if vehiculo:
        cur_cols = cursor.execute("PRAGMA table_info(viajes)")
        columnas_viajes = [col["name"] for col in cur_cols.fetchall()]

        if "vehiculo_placa" in columnas_viajes:
            cursor.execute("""
                UPDATE viajes
                SET vehiculo_id = ?, vehiculo_placa = ?, estado = 'Asignado'
                WHERE id = ?
            """, (vehiculo["id"], vehiculo["matricula"], id))
        else:
            cursor.execute(
                "UPDATE viajes SET vehiculo_id = ?, estado = 'Asignado' WHERE id = ?",
                (vehiculo["id"], id)
            )

        cursor.execute("UPDATE vehiculos SET estado = 'En viaje' WHERE id = ?", (vehiculo["id"],))

    conexion.commit()
    conexion.close()

    return redirect(f"/admin/viajes/{id}/gestionar")


@admin_bp.route("/viaje/<int:id>/asignar-todo", methods=["POST"])
def asignar_camionero_vehiculo(id):
    if not requiere_admin():
        return redirect("/login")

    camionero_id = request.form.get("camionero", "").strip()

    if not camionero_id:
        return redirect(f"/admin/viajes/{id}/gestionar?error=Selecciona+un+camionero")

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("SELECT * FROM viajes WHERE id = ?", (id,))
    viaje = cursor.fetchone()
    if not viaje:
        conexion.close()
        return redirect("/admin/viajes")

    cursor.execute("SELECT nombre FROM camioneros WHERE id = ?", (camionero_id,))
    camionero = cursor.fetchone()

    cursor.execute("""
        SELECT id, COALESCE(matricula, '') AS matricula,
               COALESCE(marca, '') AS marca, COALESCE(modelo, '') AS modelo
        FROM vehiculos
        WHERE camionero_id = ? AND activo = 1
        LIMIT 1
    """, (camionero_id,))
    vehiculo = cursor.fetchone()

    if camionero:
        cursor.execute("""
            UPDATE viajes SET camionero_id = ?, camionero_nombre = ? WHERE id = ?
        """, (camionero_id, camionero["nombre"], id))
        cursor.execute("UPDATE camioneros SET estado = 'En viaje' WHERE id = ?", (camionero_id,))

    if vehiculo:
        cur_cols = cursor.execute("PRAGMA table_info(viajes)")
        columnas_viajes = [col["name"] for col in cur_cols.fetchall()]
        if "vehiculo_placa" in columnas_viajes:
            cursor.execute("""
                UPDATE viajes SET vehiculo_id = ?, vehiculo_placa = ? WHERE id = ?
            """, (vehiculo["id"], vehiculo["matricula"], id))
        else:
            cursor.execute("UPDATE viajes SET vehiculo_id = ? WHERE id = ?", (vehiculo["id"], id))
        cursor.execute("UPDATE vehiculos SET estado = 'En viaje' WHERE id = ?", (vehiculo["id"],))

    if camionero:
        cursor.execute("UPDATE viajes SET estado = 'Asignado' WHERE id = ?", (id,))

    nombre_cam = camionero["nombre"] if camionero else "desconocido"
    nombre_veh = f"{vehiculo['marca']} {vehiculo['modelo']} ({vehiculo['matricula']})" if vehiculo else "desconocido"

    conexion.commit()
    conexion.close()

    registrar_auditoria(
        f"Asignó camionero {nombre_cam} y vehículo {nombre_veh}",
        "Viajes", "viaje", id,
        f"Camionero y vehículo asignados juntos"
    )

    return redirect(f"/admin/viajes/{id}/gestionar")


@admin_bp.route("/viaje/<int:id>/pdf")
def descargar_pdf_orden_carga(id):
    if not requiere_admin():
        return redirect("/login")

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT
            v.*,
            c.telefono  AS camionero_telefono,
            c.licencia  AS camionero_licencia,
            veh.matricula AS vehiculo_matricula,
            veh.marca     AS vehiculo_marca,
            veh.modelo    AS vehiculo_modelo,
            cl.empresa    AS cliente_empresa,
            cl.telefono   AS cliente_telefono,
            cl.email      AS cliente_email
        FROM viajes v
        LEFT JOIN camioneros c   ON v.camionero_id = c.id
        LEFT JOIN vehiculos  veh ON v.vehiculo_id  = veh.id
        LEFT JOIN clientes   cl  ON v.cliente_id   = cl.id
        WHERE v.id = ?
    """, (id,))

    fila = cursor.fetchone()
    conexion.close()

    if not fila:
        return redirect("/admin/viajes")

    viaje = dict(fila)

    faltantes_oc = []
    if not viaje.get("cliente"):
        faltantes_oc.append("cliente")
    if not viaje.get("camionero_nombre") and not viaje.get("camionero_id"):
        faltantes_oc.append("camionero")
    if not viaje.get("vehiculo_id"):
        faltantes_oc.append("vehículo")
    if not viaje.get("origen"):
        faltantes_oc.append("origen")
    if not viaje.get("destino"):
        faltantes_oc.append("destino")
    if faltantes_oc:
        msg = quote_plus("Faltan datos para Orden de Carga: " + ", ".join(faltantes_oc))
        return redirect(f"/admin/viajes/{id}/gestionar?error={msg}")

    pdf_bytes = generar_pdf_orden_carga(viaje)

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"orden-carga-{id:04d}.pdf",
    )


@admin_bp.route("/viaje/<int:id>/carta-porte")
def descargar_carta_porte(id):
    if not requiere_admin():
        return redirect("/login")
    try:
        from services.pdf_service import generar_pdf_carta_porte
        pdf_bytes = generar_pdf_carta_porte(id)
        registrar_auditoria("Descargó Carta de Porte", "Viajes", "viaje", id)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"carta-porte-{id:04d}.pdf",
        )
    except ValueError as e:
        msg = quote_plus(str(e))
        return redirect(f"/admin/viajes/{id}/gestionar?error={msg}")


@admin_bp.route("/viaje/<int:id>/liquidacion")
def descargar_liquidacion(id):
    if not requiere_admin():
        return redirect("/login")
    try:
        from services.pdf_service import generar_pdf_liquidacion_camionero
        pdf_bytes = generar_pdf_liquidacion_camionero(id)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"liquidacion-{id:04d}.pdf",
        )
    except ValueError as e:
        msg = quote_plus(str(e))
        return redirect(f"/admin/viajes/{id}/gestionar?error={msg}")


@admin_bp.route("/viaje/<int:id>/factura")
def descargar_factura_cliente(id):
    if not requiere_admin():
        return redirect("/login")

    try:
        pdf_bytes = generar_factura_cliente(id)
    except ValueError as e:
        return redirect(f"/admin/viajes/{id}/gestionar?error={e}")

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"factura-{id:04d}.pdf",
    )


@admin_bp.route("/viaje/<int:id>/confirmar-precio", methods=["POST"])
def confirmar_precio(id):
    if not requiere_admin():
        return redirect("/login")

    precio_str = request.form.get("precio_cliente", "").strip()
    try:
        precio = float(precio_str)
        if precio <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return redirect(f"/admin/viajes/{id}/gestionar?error=Precio+inv%C3%A1lido%2C+debe+ser+un+n%C3%BAmero+mayor+que+cero")

    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("UPDATE viajes SET precio_cliente = ? WHERE id = ?", (precio, id))
    conexion.commit()
    conexion.close()

    registrar_auditoria(f"Confirmó precio ${precio}", "Viajes", "viaje", id)

    return redirect(f"/admin/viajes/{id}/gestionar")


@admin_bp.route("/viaje/<int:id>/eliminar", methods=["POST"])
def eliminar_viaje_admin(id):
    if not requiere_admin():
        return redirect("/login")
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM viajes WHERE id = ?", (id,))
    conexion.commit()
    conexion.close()
    return redirect("/admin/viajes")


@admin_bp.route("/viaje/<int:id>/nota", methods=["POST"])
def agregar_nota_viaje(id):
    if not requiere_admin():
        return redirect("/login")
    texto = request.form.get("texto", "").strip()
    if texto:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute(
            "INSERT INTO notas_viaje (viaje_id, usuario, texto) VALUES (?, ?, ?)",
            (id, session.get("usuario", "admin"), texto)
        )
        conexion.commit()
        conexion.close()
    return redirect(f"/admin/viaje/{id}")


@admin_bp.route("/cotizacion/<int:id>/convertir")
@admin_bp.route("/cotizaciones/<int:id>/convertir")
def convertir_cotizacion(id):
    if not requiere_admin():
        return redirect("/login")

    viaje_id = convertir_cotizacion_en_viaje(id)

    if not viaje_id:
        return redirect("/comercial/cotizaciones")

    return redirect(f"/admin/viajes/{viaje_id}/gestionar")


# ── Camioneros CRUD ──────────────────────────────────────────────────────────

@admin_bp.route("/camioneros", methods=["GET", "POST"])
def admin_camioneros():
    if not requiere_admin():
        return redirect("/login")

    conexion = conectar()
    cursor = conexion.cursor()

    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        telefono = request.form.get("telefono", "").strip()
        licencia = request.form.get("licencia", "").strip()
        matricula = request.form.get("matricula", "").strip()
        tipo = request.form.get("tipo", "").strip()
        capacidad = request.form.get("capacidad", "").strip()
        estado = request.form.get("estado", "Disponible").strip()
        vehiculo_id = request.form.get("vehiculo_id") or None

        cursor.execute("""
            INSERT INTO camioneros (nombre, telefono, licencia, matricula, tipo, capacidad, estado)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (nombre, telefono, licencia, matricula, tipo, capacidad, estado))

        nuevo_id = cursor.lastrowid
        if vehiculo_id:
            cursor.execute(
                "UPDATE vehiculos SET camionero_id = ? WHERE id = ? AND activo = 1",
                (nuevo_id, vehiculo_id)
            )

        conexion.commit()

    buscar = request.args.get("buscar", "").strip()
    filtro_estado = request.args.get("estado", "").strip()

    condiciones = []
    params = []
    if buscar:
        condiciones.append("(nombre LIKE ? OR telefono LIKE ? OR licencia LIKE ?)")
        like = f"%{buscar}%"
        params.extend([like, like, like])
    if filtro_estado:
        condiciones.append("LOWER(estado) = ?")
        params.append(filtro_estado.lower())
    where = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""

    cursor.execute(f"""
        SELECT id, nombre, telefono, licencia, matricula, tipo, capacidad, estado
        FROM camioneros
        {where}
        ORDER BY id DESC
    """, params)
    lista = cursor.fetchall()

    cursor.execute("""
        SELECT id, COALESCE(matricula, '') AS matricula,
               COALESCE(marca, '') AS marca, COALESCE(modelo, '') AS modelo
        FROM vehiculos
        WHERE activo = 1 AND camionero_id IS NULL
        ORDER BY matricula
    """)
    vehiculos_disponibles = cursor.fetchall()

    conexion.close()

    rutas_por_camionero = {c["id"]: get_rutas_por_camionero(c["id"]) for c in lista}

    return render_template(
        "admin/camioneros.html",
        lista=lista,
        estados=CAMIONERO_ESTADOS,
        rutas_por_camionero=rutas_por_camionero,
        vehiculos_disponibles=vehiculos_disponibles,
        buscar=buscar,
        filtro_estado=filtro_estado,
    )


@admin_bp.route("/camioneros/<int:id>/editar", methods=["GET", "POST"])
def editar_camionero(id):
    if not requiere_admin():
        return redirect("/login")

    conexion = conectar()
    cursor = conexion.cursor()

    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        telefono = request.form.get("telefono", "").strip()
        licencia = request.form.get("licencia", "").strip()
        matricula = request.form.get("matricula", "").strip()
        tipo = request.form.get("tipo", "").strip()
        capacidad = request.form.get("capacidad", "").strip()
        estado = request.form.get("estado", "Disponible").strip()

        cursor.execute("""
            UPDATE camioneros
            SET nombre = ?, telefono = ?, licencia = ?, matricula = ?,
                tipo = ?, capacidad = ?, estado = ?
            WHERE id = ?
        """, (nombre, telefono, licencia, matricula, tipo, capacidad, estado, id))

        conexion.commit()
        conexion.close()

        return redirect("/admin/camioneros")

    cursor.execute("""
        SELECT id, nombre, telefono, licencia, matricula, tipo, capacidad, estado
        FROM camioneros
        WHERE id = ?
    """, (id,))
    camionero = cursor.fetchone()

    conexion.close()

    if not camionero:
        return redirect("/admin/camioneros")

    return render_template("admin/editar_camionero.html", camionero=camionero, estados=CAMIONERO_ESTADOS)


@admin_bp.route("/camioneros/<int:id>/eliminar", methods=["POST"])
def eliminar_camionero(id):
    if not requiere_admin():
        return redirect("/login")

    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM camioneros WHERE id = ?", (id,))
    conexion.commit()
    conexion.close()

    return redirect("/admin/camioneros")


# ── Clientes CRUD ────────────────────────────────────────────────────────────

@admin_bp.route("/clientes", methods=["GET", "POST"])
def admin_clientes():
    if not requiere_admin():
        return redirect("/login")

    conexion = conectar()
    cursor = conexion.cursor()

    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        empresa = request.form.get("empresa", "").strip()
        contacto = request.form.get("contacto", "").strip()
        telefono = request.form.get("telefono", "").strip()
        email = request.form.get("email", "").strip()
        direccion = request.form.get("direccion", "").strip()

        cursor.execute("""
            INSERT INTO clientes (nombre, empresa, contacto, telefono, email, direccion)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (nombre, empresa, contacto, telefono, email, direccion))

        conexion.commit()

    buscar_cl = request.args.get("buscar", "").strip()
    cond_cl = []
    params_cl = []
    if buscar_cl:
        cond_cl.append("(nombre LIKE ? OR email LIKE ? OR empresa LIKE ? OR telefono LIKE ?)")
        like_cl = f"%{buscar_cl}%"
        params_cl.extend([like_cl, like_cl, like_cl, like_cl])
    where_cl = ("WHERE " + " AND ".join(cond_cl)) if cond_cl else ""

    cursor.execute(f"""
        SELECT id, nombre, empresa, contacto, telefono, email, direccion, fecha_creacion
        FROM clientes
        {where_cl}
        ORDER BY id DESC
    """, params_cl)
    lista = cursor.fetchall()

    conexion.close()

    return render_template("admin/clientes.html", lista=lista, buscar_cl=buscar_cl)


@admin_bp.route("/clientes/<int:id>/editar", methods=["GET", "POST"])
def editar_cliente(id):
    if not requiere_admin():
        return redirect("/login")

    conexion = conectar()
    cursor = conexion.cursor()

    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        empresa = request.form.get("empresa", "").strip()
        contacto = request.form.get("contacto", "").strip()
        telefono = request.form.get("telefono", "").strip()
        email = request.form.get("email", "").strip()
        direccion = request.form.get("direccion", "").strip()

        cursor.execute("""
            UPDATE clientes
            SET nombre = ?, empresa = ?, contacto = ?, telefono = ?,
                email = ?, direccion = ?
            WHERE id = ?
        """, (nombre, empresa, contacto, telefono, email, direccion, id))

        conexion.commit()
        conexion.close()

        return redirect("/admin/clientes")

    cursor.execute("""
        SELECT id, nombre, empresa, contacto, telefono, email, direccion
        FROM clientes
        WHERE id = ?
    """, (id,))
    cliente = cursor.fetchone()

    conexion.close()

    if not cliente:
        return redirect("/admin/clientes")

    return render_template("admin/editar_cliente.html", cliente=cliente)


@admin_bp.route("/clientes/<int:id>/eliminar", methods=["POST"])
def eliminar_cliente(id):
    if not requiere_admin():
        return redirect("/login")

    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM clientes WHERE id = ?", (id,))
    conexion.commit()
    conexion.close()

    return redirect("/admin/clientes")


# ── Vehículos CRUD ──────────────────────────────────────────────────────────

@admin_bp.route("/vehiculos", methods=["GET", "POST"])
def admin_vehiculos():
    if not requiere_admin():
        return redirect("/login")

    conexion = conectar()
    cursor = conexion.cursor()

    if request.method == "POST":
        matricula = request.form["matricula"].strip()
        tipo = request.form.get("tipo", "").strip()
        marca = request.form.get("marca", "").strip()
        modelo = request.form.get("modelo", "").strip()
        capacidad = request.form.get("capacidad", "").strip()
        camionero_id = request.form.get("camionero_id") or None
        estado = request.form.get("estado", "Disponible").strip()

        cursor.execute("""
            INSERT INTO vehiculos (matricula, tipo, marca, modelo, capacidad, camionero_id, estado)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (matricula, tipo, marca, modelo, capacidad, camionero_id, estado))
        conexion.commit()

    buscar_v = request.args.get("buscar", "").strip()
    filtro_estado_v = request.args.get("estado", "").strip()

    cond_v = []
    params_v = []
    if buscar_v:
        cond_v.append("(v.matricula LIKE ? OR v.marca LIKE ? OR v.modelo LIKE ?)")
        like_v = f"%{buscar_v}%"
        params_v.extend([like_v, like_v, like_v])
    if filtro_estado_v:
        cond_v.append("LOWER(v.estado) = ?")
        params_v.append(filtro_estado_v.lower())
    where_v = "WHERE v.activo = 1" + (" AND " + " AND ".join(cond_v) if cond_v else "")

    cursor.execute(f"""
        SELECT v.id, v.matricula, v.tipo, v.marca, v.modelo, v.capacidad, v.estado,
               c.nombre AS camionero_nombre
        FROM vehiculos v
        LEFT JOIN camioneros c ON v.camionero_id = c.id
        {where_v}
        ORDER BY v.id DESC
    """, params_v)
    lista = cursor.fetchall()

    cursor.execute("SELECT id, nombre FROM camioneros WHERE activo = 1 ORDER BY nombre")
    camioneros = cursor.fetchall()

    conexion.close()

    return render_template(
        "admin/vehiculos.html",
        lista=lista,
        camioneros=camioneros,
        estados=VEHICULO_ESTADOS,
        buscar_v=buscar_v,
        filtro_estado_v=filtro_estado_v,
        estados_vehiculo=["Disponible", "En ruta", "En mantenimiento"],
    )


@admin_bp.route("/vehiculos/<int:id>/editar", methods=["GET", "POST"])
def editar_vehiculo(id):
    if not requiere_admin():
        return redirect("/login")

    conexion = conectar()
    cursor = conexion.cursor()

    if request.method == "POST":
        matricula = request.form["matricula"].strip()
        tipo = request.form.get("tipo", "").strip()
        marca = request.form.get("marca", "").strip()
        modelo = request.form.get("modelo", "").strip()
        capacidad = request.form.get("capacidad", "").strip()
        camionero_id = request.form.get("camionero_id") or None
        estado = request.form.get("estado", "Disponible").strip()

        cursor.execute("""
            UPDATE vehiculos
            SET matricula = ?, tipo = ?, marca = ?, modelo = ?,
                capacidad = ?, camionero_id = ?, estado = ?
            WHERE id = ?
        """, (matricula, tipo, marca, modelo, capacidad, camionero_id, estado, id))
        conexion.commit()
        conexion.close()
        return redirect("/admin/vehiculos")

    cursor.execute("""
        SELECT id, matricula, tipo, marca, modelo, capacidad, camionero_id, estado
        FROM vehiculos
        WHERE id = ? AND activo = 1
    """, (id,))
    vehiculo = cursor.fetchone()

    cursor.execute("SELECT id, nombre FROM camioneros WHERE activo = 1 ORDER BY nombre")
    camioneros = cursor.fetchall()

    conexion.close()

    if not vehiculo:
        return redirect("/admin/vehiculos")

    return render_template(
        "admin/editar_vehiculo.html",
        vehiculo=vehiculo,
        camioneros=camioneros,
        estados=VEHICULO_ESTADOS
    )


@admin_bp.route("/vehiculos/sugerencias")
def sugerencias_vehiculos():
    if not requiere_admin():
        return jsonify([]), 403

    campo = request.args.get("campo", "")
    q = request.args.get("q", "").strip()

    if campo not in ("marca", "modelo"):
        return jsonify([]), 400

    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute(
        f"SELECT DISTINCT {campo} FROM vehiculos"
        f" WHERE {campo} LIKE ? AND activo = 1 AND {campo} != ''"
        f" ORDER BY {campo} LIMIT 10",
        (f"%{q}%",)
    )
    resultados = [row[0] for row in cursor.fetchall() if row[0]]
    conexion.close()

    return jsonify(resultados)


@admin_bp.route("/vehiculos/<int:id>/eliminar", methods=["POST"])
def eliminar_vehiculo(id):
    if not requiere_admin():
        return redirect("/login")

    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("UPDATE vehiculos SET activo = 0 WHERE id = ?", (id,))
    conexion.commit()
    conexion.close()

    return redirect("/admin/vehiculos")


# ── Reportes ─────────────────────────────────────────────────────────────────

MESES_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
            "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def _ultimos_6_meses():
    """Devuelve lista de (year, month) para los últimos 6 meses, orden ascendente."""
    hoy = date.today()
    meses = []
    for i in range(5, -1, -1):
        m = hoy.month - i
        y = hoy.year
        while m <= 0:
            m += 12
            y -= 1
        meses.append((y, m))
    return meses


def _calcular_financieros_periodo(fecha_desde, fecha_hasta):
    """Devuelve (filas_tabla, totales) para el período dado."""
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("""
        SELECT id, cliente, origen, destino, estado, fecha_creacion
        FROM viajes
        WHERE (fecha_creacion >= ? AND fecha_creacion <= ?)
          AND LOWER(estado) != 'cancelado'
        ORDER BY id DESC
    """, (fecha_desde, fecha_hasta + " 23:59:59"))
    viajes_periodo = cursor.fetchall()
    conexion.close()

    filas = []
    totales = {"ingresos": 0.0, "pago_camionero": 0.0,
               "combustible": 0.0, "comision": 0.0, "utilidad": 0.0}

    for v in viajes_periodo:
        liq = calcular_liquidacion(v["id"])
        pc = liq["precio_cliente"] if liq else 0.0
        pag = liq["pago_camionero"] if liq else 0.0
        comb = liq["combustible"] if liq else 0.0
        com = liq["comision_mercatoria"] if liq else 0.0
        util = liq["utilidad_mercatoria"] if liq else 0.0

        totales["ingresos"] += pc
        totales["pago_camionero"] += pag
        totales["combustible"] += comb
        totales["comision"] += com
        totales["utilidad"] += util

        filas.append({
            "id": v["id"],
            "cliente": v["cliente"] or "—",
            "ruta": f"{v['origen']} → {v['destino']}",
            "estado": v["estado"],
            "precio_cliente": pc,
            "pago_camionero": pag,
            "combustible": comb,
            "utilidad": util,
        })

    return filas, totales


@admin_bp.route("/reportes")
def reportes():
    if not (session.get("usuario") and session.get("rol") == "admin"):
        return redirect("/admin?access_error=Solo+administradores+pueden+ver+reportes")

    hoy = date.today()
    fecha_desde = request.args.get("fecha_desde", hoy.replace(day=1).isoformat())
    fecha_hasta = request.args.get("fecha_hasta", hoy.isoformat())

    filas_tabla, totales = _calcular_financieros_periodo(fecha_desde, fecha_hasta)

    # KPIs adicionales
    n = len(filas_tabla)
    viaje_promedio = totales["ingresos"] / n if n else 0.0

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT origen || ' → ' || destino AS ruta,
               COUNT(*) AS viajes,
               SUM(COALESCE(precio_final, precio_cliente, precio, 0)) AS ingresos_proxy
        FROM viajes
        WHERE (fecha_creacion >= ? AND fecha_creacion <= ?)
          AND LOWER(estado) != 'cancelado'
        GROUP BY ruta
        ORDER BY ingresos_proxy DESC
        LIMIT 1
    """, (fecha_desde, fecha_hasta + " 23:59:59"))
    ruta_top = cursor.fetchone()

    cursor.execute("""
        SELECT camionero_nombre, COUNT(*) AS total_viajes
        FROM viajes
        WHERE (fecha_creacion >= ? AND fecha_creacion <= ?)
          AND LOWER(estado) != 'cancelado'
          AND camionero_nombre IS NOT NULL AND camionero_nombre != ''
        GROUP BY camionero_nombre
        ORDER BY total_viajes DESC
        LIMIT 1
    """, (fecha_desde, fecha_hasta + " 23:59:59"))
    camionero_top = cursor.fetchone()

    # Datos mensuales (últimos 6 meses) para el gráfico
    cursor.execute("""
        SELECT strftime('%Y-%m', fecha_creacion) AS mes,
               SUM(COALESCE(precio_final, precio_cliente, precio, 0)) AS ingresos
        FROM viajes
        WHERE fecha_creacion >= date('now', '-5 months', 'start of month')
          AND LOWER(estado) != 'cancelado'
        GROUP BY mes
        ORDER BY mes
    """)
    datos_db = {row["mes"]: float(row["ingresos"] or 0) for row in cursor.fetchall()}
    conexion.close()

    # Rellenar los 6 meses aunque no haya datos
    meses_base = _ultimos_6_meses()
    chart_labels = [f"{MESES_ES[m-1]} {y}" for y, m in meses_base]
    chart_data = [datos_db.get(f"{y:04d}-{m:02d}", 0.0) for y, m in meses_base]

    return render_template(
        "admin/reportes.html",
        filas_tabla=filas_tabla,
        totales=totales,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        chart_labels=json.dumps(chart_labels),
        chart_data=json.dumps(chart_data),
        viaje_promedio=round(viaje_promedio, 2),
        ruta_top=ruta_top,
        camionero_top=camionero_top,
        total_viajes=n,
    )


@admin_bp.route("/reportes/exportar")
def exportar_reportes_csv():
    if not (session.get("usuario") and session.get("rol") == "admin"):
        return redirect("/admin?access_error=Solo+administradores+pueden+ver+reportes")

    hoy = date.today()
    fecha_desde = request.args.get("fecha_desde", hoy.replace(day=1).isoformat())
    fecha_hasta = request.args.get("fecha_hasta", hoy.isoformat())

    filas, totales = _calcular_financieros_periodo(fecha_desde, fecha_hasta)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Cliente", "Ruta", "Estado",
                     "Precio Cliente (USD)", "Pago Camionero (USD)",
                     "Combustible (USD)", "Utilidad (USD)"])
    for f in filas:
        writer.writerow([
            f["id"], f["cliente"], f["ruta"], f["estado"],
            f"{f['precio_cliente']:.2f}", f"{f['pago_camionero']:.2f}",
            f"{f['combustible']:.2f}", f"{f['utilidad']:.2f}",
        ])
    writer.writerow([])
    writer.writerow(["TOTALES", "", "", "",
                     f"{totales['ingresos']:.2f}", f"{totales['pago_camionero']:.2f}",
                     f"{totales['combustible']:.2f}", f"{totales['utilidad']:.2f}"])

    csv_bytes = output.getvalue().encode("utf-8-sig")
    nombre = f"reporte-{fecha_desde}-{fecha_hasta}.csv"
    return send_file(
        io.BytesIO(csv_bytes),
        mimetype="text/csv",
        as_attachment=True,
        download_name=nombre,
    )


# ── Usuarios CRUD ─────────────────────────────────────────────────────────────

@admin_bp.route("/usuarios", methods=["GET"])
def lista_usuarios():
    if session.get("rol") != "admin":
        return redirect("/login")

    filtro_rol = request.args.get("rol", "").strip().lower()

    conexion = conectar()
    cursor = conexion.cursor()

    if filtro_rol:
        cursor.execute("""
            SELECT id, usuario, rol, activo, fecha_creacion
            FROM usuarios
            WHERE rol = ?
            ORDER BY id DESC
        """, (filtro_rol,))
    else:
        cursor.execute("""
            SELECT id, usuario, rol, activo, fecha_creacion
            FROM usuarios
            ORDER BY id DESC
        """)
    lista = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) AS total FROM usuarios")
    total = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) AS total FROM usuarios WHERE rol = 'admin'")
    total_admin = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) AS total FROM usuarios WHERE rol = 'operador'")
    total_operador = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) AS total FROM usuarios WHERE rol = 'cliente'")
    total_cliente = cursor.fetchone()["total"]

    conexion.close()

    return render_template(
        "admin/usuarios.html",
        usuarios=lista,
        filtro_rol=filtro_rol,
        total=total,
        total_admin=total_admin,
        total_operador=total_operador,
        total_cliente=total_cliente,
    )


@admin_bp.route("/usuarios/crear", methods=["POST"])
def crear_usuario():
    if session.get("rol") != "admin":
        return redirect("/admin")

    usuario = request.form.get("usuario", "").strip()
    password = request.form.get("password", "").strip()
    rol = request.form.get("rol", "").strip()

    if not usuario or not password or rol not in ("admin", "operador", "cliente"):
        return redirect("/admin/usuarios?error=Datos+inv%C3%A1lidos")

    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("SELECT id FROM usuarios WHERE usuario = ?", (usuario,))
    if cursor.fetchone():
        conexion.close()
        return redirect("/admin/usuarios?error=El+usuario+ya+existe")

    hash_pw = bcrypt.generate_password_hash(password).decode("utf-8")
    cursor.execute(
        "INSERT INTO usuarios (usuario, password, rol) VALUES (?, ?, ?)",
        (usuario, hash_pw, rol)
    )
    conexion.commit()
    conexion.close()

    registrar_auditoria(f"Creó usuario {usuario} con rol {rol}", "Usuarios", "usuario")

    return redirect("/admin/usuarios")


@admin_bp.route("/usuarios/<int:id>/rol", methods=["POST"])
def cambiar_rol_usuario(id):
    if session.get("rol") != "admin":
        return redirect("/admin")

    rol = request.form.get("rol", "").strip()
    if rol not in ("admin", "operador", "cliente"):
        return redirect("/admin/usuarios?error=Rol+inv%C3%A1lido")

    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("SELECT usuario FROM usuarios WHERE id = ?", (id,))
    row = cursor.fetchone()
    if row and row["usuario"] == session.get("usuario"):
        conexion.close()
        return redirect("/admin/usuarios?error=No+puedes+cambiar+tu+propio+rol")

    cursor.execute("UPDATE usuarios SET rol = ? WHERE id = ?", (rol, id))
    conexion.commit()
    conexion.close()

    registrar_auditoria(f"Cambió rol de usuario #{id} a {rol}", "Usuarios", "usuario", id)

    return redirect("/admin/usuarios")


@admin_bp.route("/usuarios/<int:id>/toggle", methods=["POST"])
def toggle_usuario(id):
    if session.get("rol") != "admin":
        return redirect("/admin")

    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("SELECT usuario FROM usuarios WHERE id = ?", (id,))
    row = cursor.fetchone()
    if row and row["usuario"] == session.get("usuario"):
        conexion.close()
        return redirect("/admin/usuarios?error=No+puedes+desactivarte+a+ti+mismo")

    cursor.execute(
        "UPDATE usuarios SET activo = CASE WHEN activo = 1 THEN 0 ELSE 1 END WHERE id = ?",
        (id,)
    )
    conexion.commit()
    conexion.close()

    registrar_auditoria(f"Cambió estado de usuario #{id}", "Usuarios", "usuario", id)

    return redirect("/admin/usuarios")


@admin_bp.route("/usuarios/<int:id>/reset-password", methods=["POST"])
def reset_password_usuario(id):
    if not requiere_admin():
        return redirect("/login")
    nueva = request.form.get("nueva_password", "").strip()
    if len(nueva) < 4:
        return redirect("/admin/usuarios?error=La+contraseña+debe+tener+al+menos+4+caracteres")
    from extensions import bcrypt as _bcrypt
    nuevo_hash = _bcrypt.generate_password_hash(nueva).decode("utf-8")
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("UPDATE usuarios SET password = ? WHERE id = ?", (nuevo_hash, id))
    conexion.commit()
    conexion.close()
    registrar_auditoria(f"Reseteó contraseña de usuario #{id}", "Usuarios", "usuario", id)
    return redirect("/admin/usuarios?ok=Contraseña+actualizada")


# ── Exportar / Importar Excel ──────────────────────────────────────────────────

_EXCEL_CONFIG = {
    "rutas": {
        "columnas": ["id", "nombre", "origen", "destino", "zona", "km_oficiales"],
        "tabla": "rutas",
        "redirect": "/admin/comercial/rutas",
    },
    "camioneros": {
        "columnas": ["id", "nombre", "telefono", "licencia", "estado"],
        "tabla": "camioneros",
        "redirect": "/admin/camioneros",
    },
    "clientes": {
        "columnas": ["id", "nombre", "contacto", "telefono", "email", "empresa"],
        "tabla": "clientes",
        "redirect": "/admin/clientes",
    },
    "vehiculos": {
        "columnas": ["id", "nombre", "marca", "modelo", "matricula", "tipo", "capacidad", "estado"],
        "tabla": "vehiculos",
        "redirect": "/admin/vehiculos",
    },
}

_HEADER_FILL = PatternFill("solid", fgColor="E86A2C")
_HEADER_FONT = Font(bold=True, color="FFFFFF")


@admin_bp.route("/exportar/<string:tabla>", methods=["GET"])
def exportar_excel(tabla):
    if not requiere_admin():
        return redirect("/login")

    cfg = _EXCEL_CONFIG.get(tabla)
    if not cfg:
        return redirect("/admin"), 404

    conexion = conectar()
    cursor = conexion.cursor()
    cols = ", ".join(cfg["columnas"])
    cursor.execute(f"SELECT {cols} FROM {cfg['tabla']}")
    filas = cursor.fetchall()
    conexion.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = tabla.capitalize()

    for col_idx, col_name in enumerate(cfg["columnas"], start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_name.upper())
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(horizontal="center")

    for row_idx, fila in enumerate(filas, start=2):
        for col_idx, valor in enumerate(fila, start=1):
            ws.cell(row=row_idx, column=col_idx, value=valor)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    registrar_auditoria(f"Exportó Excel de {tabla}", "Datos", tabla)

    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"{tabla}.xlsx",
    )


@admin_bp.route("/importar/<string:tabla>", methods=["POST"])
def importar_excel(tabla):
    if not requiere_admin():
        return redirect("/login")

    cfg = _EXCEL_CONFIG.get(tabla)
    if not cfg:
        return redirect("/admin"), 404

    archivo = request.files.get("archivo")
    if not archivo:
        return redirect(cfg["redirect"] + "?error=No+se+recibió+archivo")

    wb = openpyxl.load_workbook(archivo, read_only=True, data_only=True)
    ws = wb.active

    columnas = cfg["columnas"]
    placeholders = ", ".join(["?"] * len(columnas))
    cols_str = ", ".join(columnas)

    conexion = conectar()
    cursor = conexion.cursor()
    importados = 0

    for fila in ws.iter_rows(min_row=2, values_only=True):
        valores = list(fila[: len(columnas)])
        if not any(v is not None for v in valores):
            continue
        try:
            cursor.execute(
                f"INSERT OR IGNORE INTO {cfg['tabla']} ({cols_str}) VALUES ({placeholders})",
                valores,
            )
            importados += cursor.rowcount
        except Exception:
            pass

    conexion.commit()
    conexion.close()

    registrar_auditoria(f"Importó Excel a {tabla} ({importados} registros)", "Datos", tabla)

    return redirect(f"{cfg['redirect']}?importado={importados}+registros")


# ── Auditoría ──────────────────────────────────────────────────────────────────

@admin_bp.route("/auditoria", methods=["GET"])
def ver_auditoria():
    if not requiere_admin():
        return redirect("/login")

    categoria = request.args.get("categoria", "").strip()
    usuario_f = request.args.get("usuario", "").strip()
    fecha_desde = request.args.get("fecha_desde", "").strip()
    fecha_hasta = request.args.get("fecha_hasta", "").strip()
    buscar = request.args.get("buscar", "").strip()
    pagina = max(1, int(request.args.get("pagina", 1) or 1))
    por_pagina = 50

    condiciones = []
    params = []

    if categoria:
        condiciones.append("categoria = ?")
        params.append(categoria)
    if usuario_f:
        condiciones.append("usuario LIKE ?")
        params.append(f"%{usuario_f}%")
    if fecha_desde:
        condiciones.append("DATE(fecha) >= ?")
        params.append(fecha_desde)
    if fecha_hasta:
        condiciones.append("DATE(fecha) <= ?")
        params.append(fecha_hasta)
    if buscar:
        condiciones.append("(accion LIKE ? OR detalle LIKE ? OR usuario LIKE ?)")
        params.extend([f"%{buscar}%", f"%{buscar}%", f"%{buscar}%"])

    where = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute(f"SELECT COUNT(*) as total FROM auditoria {where}", params)
    total = cursor.fetchone()["total"]

    offset = (pagina - 1) * por_pagina
    cursor.execute(
        f"SELECT * FROM auditoria {where} ORDER BY id DESC LIMIT ? OFFSET ?",
        params + [por_pagina, offset]
    )
    registros = cursor.fetchall()
    conexion.close()

    total_paginas = (total + por_pagina - 1) // por_pagina

    return render_template(
        "admin/auditoria.html",
        registros=registros,
        pagina=pagina,
        total_paginas=total_paginas,
        total=total,
        filtros=dict(
            categoria=categoria,
            usuario=usuario_f,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            buscar=buscar,
        ),
    )


# ── Acciones por lote ──────────────────────────────────────────────────────────

_ESTADOS_VIAJE = [
    "Solicitado", "Pendiente", "Asignado", "En ruta",
    "Carga recogida", "Entregado", "Cancelado",
]


@admin_bp.route("/lote", methods=["GET"])
def panel_lote():
    if not requiere_admin():
        return redirect("/login")

    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("""
        SELECT id, nombre, origen, destino
        FROM rutas ORDER BY COALESCE(nombre, origen)
    """)
    rutas = cursor.fetchall()
    cursor.execute("""
        SELECT id, cliente, origen, destino, estado,
               COALESCE(precio_cliente, precio_final, precio, 0) AS precio
        FROM viajes
        WHERE LOWER(estado) NOT IN ('entregado', 'cancelado')
        ORDER BY id DESC
    """)
    viajes_activos = cursor.fetchall()
    conexion.close()

    resultado = request.args.get("resultado", "")
    return render_template(
        "admin/lote.html",
        rutas=rutas,
        viajes_activos=viajes_activos,
        estados=_ESTADOS_VIAJE,
        resultado=resultado,
    )


@admin_bp.route("/lote/preview", methods=["GET"])
def lote_preview():
    if not requiere_admin():
        return jsonify({"count": 0})

    criterio = request.args.get("criterio", "")
    valor = request.args.get("valor", "").strip()

    conexion = conectar()
    cursor = conexion.cursor()

    try:
        if criterio == "sin_precio":
            cursor.execute("""
                SELECT COUNT(*) AS total FROM viajes
                WHERE LOWER(estado) NOT IN ('entregado','cancelado')
                  AND (precio_cliente IS NULL OR precio_cliente = 0)
                  AND (precio_final   IS NULL OR precio_final   = 0)
                  AND (precio         IS NULL OR precio         = 0)
            """)
        elif criterio == "estado" and valor:
            cursor.execute(
                "SELECT COUNT(*) AS total FROM viajes WHERE LOWER(estado) = LOWER(?)", (valor,)
            )
        elif criterio == "ruta" and valor:
            cursor.execute(
                "SELECT COUNT(*) AS total FROM viajes WHERE ruta_id = ?", (valor,)
            )
        else:
            cursor.execute(
                "SELECT COUNT(*) AS total FROM viajes WHERE LOWER(estado) NOT IN ('entregado','cancelado')"
            )
        count = cursor.fetchone()["total"]
    except Exception:
        count = 0
    finally:
        conexion.close()

    return jsonify({"count": count})


@admin_bp.route("/lote/precios", methods=["POST"])
def lote_precios():
    if not requiere_admin():
        return redirect("/login")

    criterio = request.form.get("criterio", "").strip()
    valor_criterio = request.form.get("valor_criterio", "").strip()
    motivo = request.form.get("motivo", "").strip()

    try:
        precio_nuevo = float(request.form.get("precio_nuevo", 0))
        if precio_nuevo <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return redirect("/admin/lote?resultado=Error:+precio+inválido")

    conexion = conectar()
    cursor = conexion.cursor()

    if criterio == "sin_precio":
        cursor.execute("""
            UPDATE viajes SET precio_cliente = ?, precio_final = ?
            WHERE LOWER(estado) NOT IN ('entregado','cancelado')
              AND (precio_cliente IS NULL OR precio_cliente = 0)
              AND (precio_final   IS NULL OR precio_final   = 0)
              AND (precio         IS NULL OR precio         = 0)
        """, (precio_nuevo, precio_nuevo))
    elif criterio == "estado" and valor_criterio:
        cursor.execute("""
            UPDATE viajes SET precio_cliente = ?, precio_final = ?
            WHERE LOWER(estado) = LOWER(?)
        """, (precio_nuevo, precio_nuevo, valor_criterio))
    elif criterio == "ruta" and valor_criterio:
        cursor.execute("""
            UPDATE viajes SET precio_cliente = ?, precio_final = ?
            WHERE ruta_id = ?
        """, (precio_nuevo, precio_nuevo, valor_criterio))
    else:
        cursor.execute("""
            UPDATE viajes SET precio_cliente = ?, precio_final = ?
            WHERE LOWER(estado) NOT IN ('entregado','cancelado')
        """, (precio_nuevo, precio_nuevo))

    n = cursor.rowcount
    conexion.commit()
    conexion.close()

    registrar_auditoria(
        f"Precio masivo ${precio_nuevo} aplicado a {n} viajes. Motivo: {motivo}",
        "Viajes", "viajes"
    )
    from urllib.parse import quote_plus as qp
    return redirect(f"/admin/lote?resultado={qp(str(n) + ' viajes actualizados con precio $' + str(precio_nuevo))}")


@admin_bp.route("/lote/estados", methods=["POST"])
def lote_estados():
    if not requiere_admin():
        return redirect("/login")

    estado_origen = request.form.get("estado_origen", "").strip()
    estado_destino = request.form.get("estado_destino", "").strip()
    motivo = request.form.get("motivo", "").strip()

    if not estado_origen or not estado_destino:
        return redirect("/admin/lote?resultado=Error:+faltan+estados")

    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute(
        "UPDATE viajes SET estado = ? WHERE LOWER(estado) = LOWER(?)",
        (estado_destino, estado_origen)
    )
    n = cursor.rowcount
    conexion.commit()
    conexion.close()

    registrar_auditoria(
        f"Cambio masivo de estado: {estado_origen} → {estado_destino} ({n} viajes). Motivo: {motivo}",
        "Viajes", "viajes"
    )
    from urllib.parse import quote_plus as qp
    return redirect(f"/admin/lote?resultado={qp(str(n) + ' viajes cambiados a ' + estado_destino)}")


@admin_bp.route("/lote/viajes-seleccionados", methods=["POST"])
def lote_seleccionados():
    if not requiere_admin():
        return redirect("/login")

    ids_raw = request.form.getlist("ids[]")
    accion = request.form.get("accion", "").strip()
    valor = request.form.get("valor", "").strip()
    motivo = request.form.get("motivo", "").strip()

    try:
        ids = [int(i) for i in ids_raw if i.isdigit()]
    except Exception:
        ids = []

    if not ids:
        return redirect("/admin/lote?resultado=Error:+no+se+seleccionaron+viajes")

    placeholders = ",".join("?" * len(ids))
    conexion = conectar()
    cursor = conexion.cursor()

    if accion == "precio":
        try:
            precio = float(valor)
        except (ValueError, TypeError):
            conexion.close()
            return redirect("/admin/lote?resultado=Error:+precio+inválido")
        cursor.execute(
            f"UPDATE viajes SET precio_cliente = ?, precio_final = ? WHERE id IN ({placeholders})",
            [precio, precio] + ids
        )
        detalle = f"precio ${precio}"
    elif accion == "estado":
        cursor.execute(
            f"UPDATE viajes SET estado = ? WHERE id IN ({placeholders})",
            [valor] + ids
        )
        detalle = f"estado '{valor}'"
    else:
        conexion.close()
        return redirect("/admin/lote?resultado=Error:+acción+desconocida")

    n = cursor.rowcount
    conexion.commit()
    conexion.close()

    registrar_auditoria(
        f"Acción manual por lote sobre {n} viajes: {detalle}. Motivo: {motivo}",
        "Viajes", "viajes"
    )
    from urllib.parse import quote_plus as qp
    return redirect(f"/admin/lote?resultado={qp(str(n) + ' viajes actualizados (' + detalle + ')')}")


# ── Mensajes masivos ───────────────────────────────────────────────────────────

def _query_emails_clientes(filtro):
    conexion = conectar()
    cursor = conexion.cursor()

    if filtro == "activos":
        cursor.execute("""
            SELECT DISTINCT cl.email FROM clientes cl
            JOIN viajes v ON v.cliente_id = cl.id
            WHERE LOWER(v.estado) NOT IN ('entregado', 'cancelado')
              AND cl.email IS NOT NULL AND cl.email != ''
        """)
    elif filtro == "zona_occidente":
        cursor.execute("""
            SELECT DISTINCT cl.email FROM clientes cl
            JOIN viajes v ON v.cliente_id = cl.id
            JOIN rutas r ON v.ruta_id = r.id
            WHERE LOWER(r.zona) = 'occidente'
              AND cl.email IS NOT NULL AND cl.email != ''
        """)
    elif filtro == "zona_centro":
        cursor.execute("""
            SELECT DISTINCT cl.email FROM clientes cl
            JOIN viajes v ON v.cliente_id = cl.id
            JOIN rutas r ON v.ruta_id = r.id
            WHERE LOWER(r.zona) = 'centro'
              AND cl.email IS NOT NULL AND cl.email != ''
        """)
    elif filtro == "zona_oriente":
        cursor.execute("""
            SELECT DISTINCT cl.email FROM clientes cl
            JOIN viajes v ON v.cliente_id = cl.id
            JOIN rutas r ON v.ruta_id = r.id
            WHERE LOWER(r.zona) = 'oriente'
              AND cl.email IS NOT NULL AND cl.email != ''
        """)
    elif filtro == "sin_viajes":
        cursor.execute("""
            SELECT cl.email FROM clientes cl
            WHERE cl.email IS NOT NULL AND cl.email != ''
              AND cl.id NOT IN (
                  SELECT DISTINCT cliente_id FROM viajes WHERE cliente_id IS NOT NULL
              )
        """)
    else:
        cursor.execute("SELECT email FROM clientes WHERE email IS NOT NULL AND email != ''")

    emails = [row["email"] for row in cursor.fetchall() if row["email"]]
    conexion.close()
    return emails


@admin_bp.route("/mensajes")
def mensajes():
    if session.get("rol") != "admin":
        return redirect("/login")

    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("""
        SELECT accion, fecha FROM auditoria
        WHERE accion LIKE 'Envió mensaje masivo%'
        ORDER BY id DESC
        LIMIT 10
    """)
    historial = cursor.fetchall()
    conexion.close()

    enviado = request.args.get("enviado")
    error = request.args.get("error")
    return render_template("admin/mensajes.html", historial=historial, enviado=enviado, error=error)


@admin_bp.route("/mensajes/preview")
def mensajes_preview():
    if session.get("rol") != "admin":
        return jsonify({"count": 0, "emails": []})

    filtro = request.args.get("filtro", "todos")
    emails = _query_emails_clientes(filtro)
    return jsonify({"count": len(emails), "emails": emails[:3]})


@admin_bp.route("/mensajes/enviar", methods=["POST"])
def mensajes_enviar():
    if session.get("rol") != "admin":
        return redirect("/login")

    asunto = request.form.get("asunto", "").strip()
    cuerpo = request.form.get("cuerpo", "").strip()
    destinatarios = request.form.get("destinatarios", "todos").strip()

    if not asunto or not cuerpo:
        return redirect("/admin/mensajes?error=Faltan+asunto+o+cuerpo")

    emails = _query_emails_clientes(destinatarios)

    from flask import current_app
    app_obj = current_app._get_current_object()

    def enviar_todos():
        with app_obj.app_context():
            for email in emails:
                try:
                    msg = Message(subject=asunto, recipients=[email])
                    msg.body = cuerpo
                    mail.send(msg)
                except Exception as e:
                    print(f"Error enviando a {email}: {e}")

    threading.Thread(target=enviar_todos, daemon=True).start()

    registrar_auditoria(
        f"Envió mensaje masivo a {len(emails)} clientes: {asunto}",
        "Clientes", "clientes", None,
        f"Filtro: {destinatarios}"
    )

    return redirect(f"/admin/mensajes?enviado={len(emails)}")
