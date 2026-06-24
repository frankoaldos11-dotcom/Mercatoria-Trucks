from flask import Blueprint, render_template, request, redirect, session
import sqlite3

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# -----------------------------------------
# CONEXIÓN A BD
# -----------------------------------------
def conectar():
    return sqlite3.connect("mercatoria.db")

# -----------------------------------------
# PROTECCIÓN
# -----------------------------------------
def requiere_admin():
    return "usuario" in session and session.get("rol") == "operador"


# -----------------------------------------
# DASHBOARD PRINCIPAL
# -----------------------------------------
@admin_bp.route("/")
def dashboard():
    if not requiere_admin():
        return redirect("/login")

    conexion = conectar()
    cursor = conexion.cursor()

    # Contadores
    cursor.execute("SELECT COUNT(*) FROM viajes WHERE estado = 'Pendiente'")
    pendientes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM viajes WHERE estado = 'En curso'")
    en_curso = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM viajes WHERE estado = 'Entregado'")
    entregados = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM camioneros")
    camioneros = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM clientes")
    clientes = cursor.fetchone()[0]

    # Lista de solicitudes pendientes
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
        en_curso=en_curso,
        entregados=entregados,
        camioneros=camioneros,
        clientes=clientes,
        lista=lista
    )


# -----------------------------------------
# LISTA DE VIAJES
# -----------------------------------------
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


# -----------------------------------------
# GESTIONAR UN VIAJE ESPECÍFICO
# -----------------------------------------
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

    cursor.execute("SELECT nombre FROM camioneros")
    camioneros = cursor.fetchall()

    conexion.close()

    return render_template("admin/gestionar_viaje.html", viaje=viaje, camioneros=camioneros)


# -----------------------------------------
# ASIGNAR CAMIONERO
# -----------------------------------------
@admin_bp.route("/viaje/<int:id>/asignar", methods=["POST"])
def asignar_camionero(id):
    if not requiere_admin():
        return redirect("/login")

    camionero = request.form["camionero"]

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        UPDATE viajes
        SET camionero_nombre = ?, estado = 'En curso'
        WHERE id = ?
    """, (camionero, id))

    conexion.commit()
    conexion.close()

    return redirect(f"/admin/viaje/{id}")


# -----------------------------------------
# CAMBIAR ESTADO
# -----------------------------------------
@admin_bp.route("/viaje/<int:id>/estado", methods=["POST"])
def cambiar_estado(id):
    if not requiere_admin():
        return redirect("/login")

    estado = request.form["estado"]

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("UPDATE viajes SET estado = ? WHERE id = ?", (estado, id))
    conexion.commit()
    conexion.close()

    return redirect(f"/admin/viaje/{id}")


# -----------------------------------------
# GESTIÓN DE CAMIONEROS
# -----------------------------------------
@admin_bp.route("/camioneros")
def admin_camioneros():
    if not requiere_admin():
        return redirect("/login")

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("SELECT id, nombre, telefono FROM camioneros")
    lista = cursor.fetchall()

    conexion.close()

    return render_template("admin/camioneros.html", lista=lista)


# -----------------------------------------
# GESTIÓN DE CLIENTES
# -----------------------------------------
@admin_bp.route("/clientes")
def admin_clientes():
    if not requiere_admin():
        return redirect("/login")

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("SELECT id, nombre, telefono, usuario FROM clientes")
    lista = cursor.fetchall()

    conexion.close()

    return render_template("admin/clientes.html", lista=lista)
