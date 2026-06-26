import csv
import io
import json
from datetime import date, datetime
from urllib.parse import quote_plus

from flask import Blueprint, render_template, request, redirect, send_file, session, jsonify
import sqlite3

from extensions import bcrypt
from services.comercial_service import convertir_cotizacion_en_viaje, get_rutas_por_camionero
from services.finanzas_service import calcular_liquidacion
from services.pdf_service import generar_factura_cliente, generar_pdf_orden_carga
from utils.constants import CAMIONERO_ESTADOS, VEHICULO_ESTADOS

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def conectar():
    conexion = sqlite3.connect("mercatoria.db")
    conexion.row_factory = sqlite3.Row
    return conexion


def requiere_admin():
    return "usuario" in session and session.get("rol") in ["admin", "operador"]


@admin_bp.route("/")
def dashboard():
    if not requiere_admin():
        return redirect("/login")

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("SELECT COUNT(*) FROM viajes WHERE LOWER(estado) IN ('pendiente', 'solicitado')")
    pendientes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM viajes WHERE LOWER(estado) IN ('en ruta', 'en_ruta')")
    en_curso = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM viajes WHERE LOWER(estado) = 'entregado'")
    entregados = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM viajes WHERE LOWER(estado) = 'asignado'")
    asignados = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM viajes WHERE LOWER(estado) = 'cancelado'")
    cancelados = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM camioneros")
    camioneros = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM clientes")
    clientes = cursor.fetchone()[0]

    cursor.execute("""
        SELECT id, cliente, origen, destino, estado
        FROM viajes
        WHERE LOWER(estado) IN ('pendiente', 'solicitado')
        ORDER BY id DESC
    """)
    lista = cursor.fetchall()

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
        lista=lista
    )


@admin_bp.route("/viajes")
def viajes():
    if not requiere_admin():
        return redirect("/login")

    filtro = request.args.get("estado", "").strip().lower()

    conexion = conectar()
    cursor = conexion.cursor()

    if filtro:
        cursor.execute("""
            SELECT id, cliente, origen, destino, estado, camionero_nombre
            FROM viajes
            WHERE LOWER(estado) = ?
            ORDER BY id DESC
        """, (filtro,))
    else:
        cursor.execute("""
            SELECT id, cliente, origen, destino, estado, camionero_nombre
            FROM viajes
            ORDER BY id DESC
        """)
    lista = cursor.fetchall()

    conexion.close()

    return render_template("admin/viajes.html", lista=lista, filtro=filtro)


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
        SELECT v.*, v.camionero_id as cam_id
        FROM viajes v
        WHERE v.id = ?
    """, (id,))
    viaje = cursor.fetchone()

    if not viaje:
        conexion.close()
        return redirect("/admin/viajes")

    cursor.execute("""
        SELECT c.id, c.nombre,
               v.id AS vehiculo_id,
               COALESCE(v.matricula, '') AS vehiculo_matricula,
               COALESCE(v.marca, '') AS vehiculo_marca,
               COALESCE(v.modelo, '') AS vehiculo_modelo
        FROM camioneros c
        LEFT JOIN vehiculos v ON v.camionero_id = c.id AND v.activo = 1
        WHERE LOWER(c.estado) = 'disponible'
        ORDER BY c.nombre
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
        "solicitado": ["Asignado", "Cancelado"],
        "pendiente":  ["Asignado", "Cancelado"],
        "asignado":   ["En ruta", "Cancelado"],
        "en ruta":    ["Entregado", "Cancelado"],
        "en_ruta":    ["Entregado", "Cancelado"],
        "entregado":  ["En ruta", "Cancelado"],
        "cancelado":  ["Solicitado"],
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

        cursor.execute("UPDATE camioneros SET estado = 'En viaje' WHERE id = ?", (camionero_id,))

    conexion.commit()
    conexion.close()

    return redirect(f"/admin/viajes/{id}/gestionar")


@admin_bp.route("/viaje/<int:id>/estado", methods=["POST"])
def cambiar_estado(id):
    if not requiere_admin():
        return redirect("/login")

    estado = request.form["estado"]

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT camionero_id, vehiculo_id, precio_final, precio_cliente, precio, estado
        FROM viajes WHERE id = ?
    """, (id,))
    viaje = cursor.fetchone()

    if estado == "Asignado":
        if not viaje or not viaje["camionero_id"] or not viaje["vehiculo_id"]:
            conexion.close()
            return redirect(f"/admin/viajes/{id}/gestionar?error=Para+pasar+a+Asignado+debes+asignar+un+camionero+y+un+veh%C3%ADculo")

    if estado == "En ruta":
        if not viaje or not viaje["camionero_id"] or not viaje["vehiculo_id"]:
            conexion.close()
            return redirect(f"/admin/viajes/{id}/gestionar?error=Para+pasar+a+En+ruta+se+requiere+camionero+y+veh%C3%ADculo+asignados")
        precio_ok = (
            float(viaje["precio_final"] or 0) > 0
            or float(viaje["precio_cliente"] or 0) > 0
            or float(viaje["precio"] or 0) > 0
        ) if viaje else False
        if not precio_ok:
            conexion.close()
            return redirect(f"/admin/viajes/{id}/gestionar?error=No+se+puede+poner+En+ruta+sin+precio+cliente+confirmado")

    cursor.execute("UPDATE viajes SET estado = ? WHERE id = ?", (estado, id))

    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if estado == "Asignado":
        cursor.execute("UPDATE viajes SET fecha_asignacion = ? WHERE id = ?", (ahora, id))
    elif estado in ["En ruta", "Carga recogida"]:
        cursor.execute("UPDATE viajes SET fecha_recogida = ? WHERE id = ?", (ahora, id))
    elif estado == "Entregado":
        cursor.execute("UPDATE viajes SET fecha_entrega = ? WHERE id = ?", (ahora, id))

    if estado.lower() in ["entregado", "cancelado"]:
        if viaje and viaje["camionero_id"]:
            cursor.execute(
                "UPDATE camioneros SET estado = 'Disponible' WHERE id = ?",
                (viaje["camionero_id"],)
            )
        if viaje and viaje["vehiculo_id"]:
            cursor.execute(
                "UPDATE vehiculos SET estado = 'Disponible' WHERE id = ?",
                (viaje["vehiculo_id"],)
            )

    conexion.commit()
    conexion.close()

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
        SELECT id, COALESCE(matricula, '') AS matricula
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

    conexion.commit()
    conexion.close()

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

    return redirect(f"/admin/viajes/{id}/gestionar")


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

    cursor.execute("""
        SELECT id, nombre, telefono, licencia, matricula, tipo, capacidad, estado
        FROM camioneros
        ORDER BY id DESC
    """)
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

    cursor.execute("""
        SELECT id, nombre, empresa, contacto, telefono, email, direccion
        FROM clientes
        ORDER BY id DESC
    """)
    lista = cursor.fetchall()

    conexion.close()

    return render_template("admin/clientes.html", lista=lista)


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

    cursor.execute("""
        SELECT v.id, v.matricula, v.tipo, v.marca, v.modelo, v.capacidad, v.estado,
               c.nombre AS camionero_nombre
        FROM vehiculos v
        LEFT JOIN camioneros c ON v.camionero_id = c.id
        WHERE v.activo = 1
        ORDER BY v.id DESC
    """)
    lista = cursor.fetchall()

    cursor.execute("SELECT id, nombre FROM camioneros WHERE activo = 1 ORDER BY nombre")
    camioneros = cursor.fetchall()

    conexion.close()

    return render_template(
        "admin/vehiculos.html",
        lista=lista,
        camioneros=camioneros,
        estados=VEHICULO_ESTADOS
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

    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("""
        SELECT id, usuario, rol, activo, fecha_creacion
        FROM usuarios
        ORDER BY id DESC
    """)
    lista = cursor.fetchall()
    conexion.close()

    return render_template("admin/usuarios.html", lista=lista)


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

    return redirect("/admin/usuarios")
