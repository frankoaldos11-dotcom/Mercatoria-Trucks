from flask import Blueprint, render_template, request, redirect
import sqlite3

camioneros_bp = Blueprint("camioneros", __name__)


def conectar():
    return sqlite3.connect("mercatoria.db")


@camioneros_bp.route("/camioneros", methods=["GET", "POST"])
def camioneros():
    conexion = conectar()
    cursor = conexion.cursor()

    if request.method == "POST":
        nombre = request.form["nombre"]
        telefono = request.form["telefono"]
        matricula = request.form["matricula"]
        tipo = request.form["tipo"]
        capacidad = request.form["capacidad"]
        estado = request.form["estado"]

        cursor.execute("""
        INSERT INTO camioneros
        (nombre, telefono, matricula, tipo, capacidad, estado)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (nombre, telefono, matricula, tipo, capacidad, estado))

        conexion.commit()

    cursor.execute("SELECT * FROM camioneros ORDER BY id DESC")
    camioneros_guardados = cursor.fetchall()

    cursor.execute("""
    SELECT id, cliente, origen, destino
    FROM viajes
    WHERE estado IN ('Pendiente', 'Asignado')
    ORDER BY id DESC
    """)
    viajes_pendientes = cursor.fetchall()

    conexion.close()

    return render_template(
        "camioneros.html",
        camioneros=camioneros_guardados,
        viajes=viajes_pendientes
    )


@camioneros_bp.route("/asignar/<int:viaje_id>/<int:camionero_id>")
def asignar_camionero(viaje_id, camionero_id):
    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("SELECT nombre FROM camioneros WHERE id=?", (camionero_id,))
    camionero = cursor.fetchone()

    if camionero:
        camionero_nombre = camionero[0]

        cursor.execute("""
        UPDATE viajes
        SET camionero_id=?, camionero_nombre=?, estado='Asignado'
        WHERE id=?
        """, (camionero_id, camionero_nombre, viaje_id))

        cursor.execute("""
        UPDATE camioneros
        SET estado='En viaje'
        WHERE id=?
        """, (camionero_id,))

    conexion.commit()
    conexion.close()

    return redirect("/viajes")