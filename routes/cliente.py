from flask import Blueprint, render_template, request, session, redirect
import sqlite3

cliente_bp = Blueprint("cliente", __name__, url_prefix="/cliente")

# -----------------------------------------
# CONEXIÓN A BD
# -----------------------------------------
def conectar():
    return sqlite3.connect("mercatoria.db")


# -----------------------------------------
# PROTECCIÓN
# -----------------------------------------
def requiere_cliente():
    return "usuario" in session and session.get("rol") == "cliente"


# -----------------------------------------
# HOME DEL CLIENTE
# -----------------------------------------
@cliente_bp.route("/")
def cliente_home():
    if not requiere_cliente():
        return redirect("/login")

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT id, origen, destino, estado
        FROM viajes
        WHERE cliente = ?
        ORDER BY id DESC
        LIMIT 5
    """, (session["usuario"],))

    viajes = cursor.fetchall()
    conexion.close()

    return render_template("cliente/home.html", viajes=viajes)


# -----------------------------------------
# NUEVA SOLICITUD (GET + POST)
# -----------------------------------------
@cliente_bp.route("/solicitar", methods=["GET", "POST"])
def solicitar_envio():
    if not requiere_cliente():
        return redirect("/login")

    if request.method == "POST":
        origen = request.form["origen"].strip()
        destino = request.form["destino"].strip()
        tipo = request.form["tipo"].strip()
        peso = request.form["peso"].strip()
        notas = request.form["notas"].strip()

        if origen == "" or destino == "" or tipo == "" or peso == "":
            return render_template("cliente/solicitar.html", error="Todos los campos obligatorios deben estar llenos")

        conexion = conectar()
        cursor = conexion.cursor()

        cursor.execute("""
            INSERT INTO viajes (cliente, origen, destino, precio, combustible, camionero, comision, beneficio, estado, observaciones)
            VALUES (?, ?, ?, 0, 0, '', 0, 0, 'Pendiente', ?)
        """, (session["usuario"], origen, destino, notas))

        conexion.commit()
        conexion.close()

        return redirect("/cliente")

    return render_template("cliente/solicitar.html")


# -----------------------------------------
# ESTADO DE ENVÍOS ACTIVOS
# -----------------------------------------
@cliente_bp.route("/activos")
def activos():
    if not requiere_cliente():
        return redirect("/login")

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT id, origen, destino, estado, camionero_nombre
        FROM viajes
        WHERE cliente = ? AND estado != 'Entregado'
        ORDER BY id DESC
    """, (session["usuario"],))

    viajes = cursor.fetchall()
    conexion.close()

    return render_template("cliente/activos.html", viajes=viajes)


# -----------------------------------------
# HISTORIAL DE ENVÍOS
# -----------------------------------------
@cliente_bp.route("/historico")
def historico():
    if not requiere_cliente():
        return redirect("/login")

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT id, origen, destino, estado, camionero_nombre
        FROM viajes
        WHERE cliente = ? AND estado = 'Entregado'
        ORDER BY id DESC
    """, (session["usuario"],))

    viajes = cursor.fetchall()
    conexion.close()

    return render_template("cliente/historico.html", viajes=viajes)


# -----------------------------------------
# PERFIL DEL CLIENTE (VER + EDITAR)
# -----------------------------------------
@cliente_bp.route("/perfil", methods=["GET