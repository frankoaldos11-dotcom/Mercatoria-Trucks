from flask import Blueprint, render_template, request, redirect, session
import sqlite3

from services.comercial_service import convertir_cotizacion_en_viaje
from utils.constants import CAMIONERO_ESTADOS

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

    cursor.execute("SELECT COUNT(*) FROM viajes WHERE LOWER(estado) = 'pendiente'")
    pendientes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM viajes WHERE LOWER(estado) IN ('en ruta', 'en_ruta')")
    en_ruta = cursor.fetchone()[0]

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
        SELECT id, cliente, origen, destino
        FROM viajes
        WHERE LOWER(estado) = 'pendiente'
        ORDER BY id DESC
    """)
    lista = cursor.fetchall()

    conexion.close()

    return render_template(
        "admin/dashboard.html",
        pendientes=pendientes,
        en_ruta=en_ruta,
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

    conexion.close()

    return render_template(
        "admin/gestionar_viaje.html",
        viaje=viaje,
        camioneros=camioneros,
        vehiculos=vehiculos
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

    cursor.execute("SELECT camionero_id, vehiculo_id FROM viajes WHERE id = ?", (id,))
    viaje = cursor.fetchone()

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

    return render_template("admin/camioneros.html", lista=lista, estados=CAMIONERO_ESTADOS)


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
