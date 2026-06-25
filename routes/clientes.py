from flask import Blueprint, render_template, request, redirect, session
import sqlite3

clientes_bp = Blueprint("clientes", __name__)


def conectar():
    return sqlite3.connect("mercatoria.db")


def requiere_admin():
    return "usuario" in session and session.get("rol") in ["admin", "operador"]


@clientes_bp.route("/clientes", methods=["GET", "POST"])
def clientes():
    if not requiere_admin():
        return redirect("/login")

    conexion = conectar()
    cursor = conexion.cursor()

    if request.method == "POST":
        nombre = request.form["nombre"]
        contacto = request.form["contacto"]
        telefono = request.form["telefono"]
        email = request.form["email"]

        cursor.execute("""
        INSERT INTO clientes (nombre, contacto, telefono, email)
        VALUES (?, ?, ?, ?)
        """, (nombre, contacto, telefono, email))

        conexion.commit()

    cursor.execute("""
    SELECT id, nombre, contacto, telefono, email
    FROM clientes
    ORDER BY id DESC
    """)

    clientes_guardados = cursor.fetchall()
    conexion.close()

    return render_template("clientes.html", clientes=clientes_guardados)

def get_all_clientes():
    con = conectar()
    cur = con.cursor()
    cur.execute("SELECT id, nombre FROM clientes ORDER BY nombre")
    rows = cur.fetchall()
    con.close()
    return rows