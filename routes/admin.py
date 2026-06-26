import io

from flask import Blueprint, render_template, request, redirect, send_file, session, jsonify
import sqlite3

from services.comercial_service import convertir_cotizacion_en_viaje, get_rutas_por_camionero
from services.finanzas_service import calcular_liquidacion
from services.pdf_service import generar_pdf_orden_carga
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

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT id, cliente, origen, destino, estado, camionero_nombre
        FROM viajes
        ORDER BY id DESC
    """)
    lista = cursor.fetchall()

    conexion.close()

    return render_template("admin/viajes.html", lista=lista)


@admin_bp.route("/viaje/<int:id>")
@admin_bp.route("/viajes/<int:id>/gestionar")
def gestionar_viaje(id):
    if not requiere_admin():
        return redirect("/login")

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("SELECT * FROM viajes WHERE id = ?", (id,))
    viaje = cursor.fetchone()

    if not viaje:
        conexion.close()
        return redirect("/admin/viajes")

    cursor.execute("""
        SELECT id, nombre
        FROM camioneros
        WHERE LOWER(estado) = 'disponible'
        ORDER BY nombre
    """)
    camioneros = cursor.fetchall()

    cursor.execute("""
        SELECT v.id, v.matricula, v.marca, v.modelo, v.capacidad, v.tipo, v.estado
        FROM vehiculos v
        WHERE
            v.activo = 1
            AND LOWER(v.estado) = 'disponible'
            AND (
                v.tipo_vehiculo_id = ?
                OR v.tipo = (SELECT nombre FROM tipos_vehiculo WHERE id = ?)
            )
        ORDER BY v.matricula ASC
    """, (viaje["tipo_vehiculo_id"], viaje["tipo_vehiculo_id"]))
    vehiculos = cursor.fetchall()

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

    conexion.close()

    liquidacion = calcular_liquidacion(id)
    error = request.args.get("error")

    return render_template(
        "admin/gestionar_viaje.html",
        viaje=viaje,
        camioneros=camioneros,
        vehiculos=vehiculos,
        liquidacion=liquidacion,
        tipo_vehiculo_nombre=tipo_vehiculo_nombre,
        tarifa_info=tarifa_info,
        error=error,
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
        SELECT camionero_id, vehiculo_id, precio_final, precio_cliente, precio
        FROM viajes WHERE id = ?
    """, (id,))
    viaje = cursor.fetchone()

    if estado == "Asignado":
        if not viaje or not viaje["camionero_id"] or not viaje["vehiculo_id"]:
            conexion.close()
            return redirect(f"/admin/viajes/{id}/gestionar?error=Para+pasar+a+Asignado+debes+asignar+un+camionero+y+un+veh%C3%ADculo")

    if estado == "En ruta":
        precio_ok = (
            float(viaje["precio_final"] or 0) > 0
            or float(viaje["precio_cliente"] or 0) > 0
            or float(viaje["precio"] or 0) > 0
        ) if viaje else False
        if not precio_ok:
            conexion.close()
            return redirect(f"/admin/viajes/{id}/gestionar?error=No+se+puede+poner+En+ruta+sin+precio+cliente+confirmado")

    cursor.execute("UPDATE viajes SET estado = ? WHERE id = ?", (estado, id))

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
    vehiculo_id = request.form.get("vehiculo", "").strip()

    if not camionero_id or not vehiculo_id:
        return redirect(f"/admin/viajes/{id}/gestionar?error=Selecciona+un+camionero+y+un+veh%C3%ADculo")

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
        SELECT v.id, v.matricula, v.tipo_vehiculo_id, v.tipo, v.estado
        FROM vehiculos v
        WHERE v.id = ? AND v.activo = 1 AND LOWER(v.estado) = 'disponible'
        AND (
            v.tipo_vehiculo_id = ?
            OR v.tipo = (SELECT nombre FROM tipos_vehiculo WHERE id = ?)
        )
    """, (vehiculo_id, viaje["tipo_vehiculo_id"], viaje["tipo_vehiculo_id"]))
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

    if camionero and vehiculo:
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
    pdf_bytes = generar_pdf_orden_carga(viaje)

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"orden-carga-{id:04d}.pdf",
    )


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

        cursor.execute("""
            INSERT INTO camioneros (nombre, telefono, licencia, matricula, tipo, capacidad, estado)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (nombre, telefono, licencia, matricula, tipo, capacidad, estado))

        conexion.commit()

    cursor.execute("""
        SELECT id, nombre, telefono, licencia, matricula, tipo, capacidad, estado
        FROM camioneros
        ORDER BY id DESC
    """)
    lista = cursor.fetchall()

    conexion.close()

    rutas_por_camionero = {c["id"]: get_rutas_por_camionero(c["id"]) for c in lista}

    return render_template(
        "admin/camioneros.html",
        lista=lista,
        estados=CAMIONERO_ESTADOS,
        rutas_por_camionero=rutas_por_camionero,
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
