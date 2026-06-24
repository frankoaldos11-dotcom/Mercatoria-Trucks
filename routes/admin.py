from flask import Blueprint, render_template, request, redirect, session
import sqlite3

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def conectar():
    return sqlite3.connect("mercatoria.db")


def requiere_admin():
    return "usuario" in session and session.get("rol") in ["admin", "operador"]


@admin_bp.route("/")
def dashboard():
    if not requiere_admin():
        return redirect("/login")

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("SELECT COUNT(*) FROM viajes WHERE estado = 'Pendiente'")
    pendientes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM viajes WHERE estado = 'En ruta'")
    en_ruta = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM viajes WHERE estado = 'Entregado'")
    entregados = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM viajes WHERE estado = 'Asignado'")
    asignados = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM viajes WHERE estado = 'Cancelado'")
    cancelados = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM camioneros")
    camioneros = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM clientes")
    clientes = cursor.fetchone()[0]

    cursor.execute("""
        SELECT id, cliente, origen, destino
        FROM viajes
        WHERE estado = 'Pendiente'
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
def gestionar_viaje(id):
    if not requiere_admin():
        return redirect("/login")

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT id, cliente, origen, destino, estado, camionero_nombre, observaciones
        FROM viajes
        WHERE id = ?
    """, (id,))
    viaje = cursor.fetchone()

    cursor.execute("""
        SELECT id, nombre
        FROM camioneros
        WHERE estado = 'Disponible'
        ORDER BY nombre
    """)
    camioneros = cursor.fetchall()

    conexion.close()

    return render_template(
        "admin/gestionar_viaje.html",
        viaje=viaje,
        camioneros=camioneros
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
        camionero_nombre = fila[0]

        cursor.execute("""
            UPDATE viajes
            SET camionero_id = ?,
                camionero_nombre = ?,
                estado = 'Asignado'
            WHERE id = ?
        """, (camionero_id, camionero_nombre, id))

        cursor.execute("""
            UPDATE camioneros
            SET estado = 'En viaje'
            WHERE id = ?
        """, (camionero_id,))

    conexion.commit()
    conexion.close()

    return redirect(f"/admin/viaje/{id}")


@admin_bp.route("/viaje/<int:id>/estado", methods=["POST"])
def cambiar_estado(id):
    if not requiere_admin():
        return redirect("/login")

    estado = request.form["estado"]

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("UPDATE viajes SET estado = ? WHERE id = ?", (estado, id))

    if estado in ["Entregado", "Cancelado"]:
        cursor.execute("SELECT camionero_id FROM viajes WHERE id = ?", (id,))
        fila = cursor.fetchone()

        if fila and fila[0]:
            cursor.execute("""
                UPDATE camioneros
                SET estado = 'Disponible'
                WHERE id = ?
            """, (fila[0],))

    conexion.commit()
    conexion.close()

    return redirect(f"/admin/viaje/{id}")


@admin_bp.route("/camioneros")
def admin_camioneros():
    if not requiere_admin():
        return redirect("/login")

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT id, nombre, telefono
        FROM camioneros
        ORDER BY id DESC
    """)
    lista = cursor.fetchall()

    conexion.close()

    return render_template("admin/camioneros.html", lista=lista)


@admin_bp.route("/clientes")
def admin_clientes():
    if not requiere_admin():
        return redirect("/login")

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT id, nombre, telefono, email
        FROM clientes
        ORDER BY id DESC
    """)
    lista = cursor.fetchall()

    conexion.close()

    return render_template("admin/clientes.html", lista=lista)