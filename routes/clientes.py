from flask import Blueprint, render_template, request
import sqlite3

clientes_bp = Blueprint("clientes", __name__)


def conectar():
    return sqlite3.connect("mercatoria.db")


@clientes_bp.route("/clientes", methods=["GET", "POST"])
def clientes():
    conexion = conectar()
    cursor = conexion.cursor()

    if request.method == "POST":
        nombre = request.form["nombre"]
        contacto = request.form["contacto"]
        telefono = request.form["telefono"]
        email = request.form["email"]

        cursor.execute("""
        INSERT INTO clientes
        (nombre, contacto, telefono, email)
        VALUES (?, ?, ?, ?)
        """, (nombre, contacto, telefono, email))

        conexion.commit()

    cursor.execute("SELECT * FROM clientes ORDER BY id DESC")
    clientes_guardados = cursor.fetchall()

    conexion.close()

    return render_template("clientes.html", clientes=clientes_guardados)