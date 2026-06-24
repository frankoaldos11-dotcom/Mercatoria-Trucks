from flask import Blueprint, render_template, request, redirect
import sqlite3

viajes_bp = Blueprint("viajes", __name__)

COMISION_MERCATORIA = 0.20
CURRENT_ROLE = "MASTER"


def conectar():
    return sqlite3.connect("mercatoria.db")


@viajes_bp.route("/nuevo-viaje", methods=["GET", "POST"])
def nuevo_viaje():
    if request.method == "POST":
        cliente = request.form["cliente"]
        origen = request.form["origen"]
        destino = request.form["destino"]
        precio = float(request.form["precio"])
        combustible = float(request.form["combustible"])
        pago_camionero = float(request.form["camionero"])
        observaciones = request.form.get("observaciones", "")

        comision = precio * COMISION_MERCATORIA
        beneficio = precio - combustible - pago_camionero

        conexion = conectar()
        cursor = conexion.cursor()

        cursor.execute("""
        INSERT INTO viajes
        (cliente, origen, destino, precio, combustible, camionero,
         comision, beneficio, estado, observaciones)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cliente, origen, destino, precio, combustible, pago_camionero,
            comision, beneficio, "Pendiente", observaciones
        ))

        conexion.commit()
        conexion.close()

        return redirect("/viajes")

    return render_template("nuevo_viaje.html")


@viajes_bp.route("/viajes")
def viajes():
    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
    SELECT id, cliente, origen, destino, precio, combustible, camionero,
           comision, beneficio, estado, camionero_nombre, observaciones
    FROM viajes
    ORDER BY id DESC
    """)

    viajes_guardados = cursor.fetchall()
    conexion.close()

    return render_template("viajes.html", viajes=viajes_guardados, rol=CURRENT_ROLE)


@viajes_bp.route("/editar/<int:id>", methods=["GET", "POST"])
def editar_viaje(id):
    conexion = conectar()
    cursor = conexion.cursor()

    if request.method == "POST":
        cliente = request.form["cliente"]
        origen = request.form["origen"]
        destino = request.form["destino"]
        precio = float(request.form["precio"])
        combustible = float(request.form["combustible"])
        pago_camionero = float(request.form["camionero"])
        estado = request.form["estado"]
        observaciones = request.form.get("observaciones", "")

        comision = precio * COMISION_MERCATORIA
        beneficio = precio - combustible - pago_camionero

        cursor.execute("""
        UPDATE viajes
        SET cliente=?, origen=?, destino=?, precio=?, combustible=?,
            camionero=?, comision=?, beneficio=?, estado=?, observaciones=?
        WHERE id=?
        """, (
            cliente, origen, destino, precio, combustible, pago_camionero,
            comision, beneficio, estado, observaciones, id
        ))

        conexion.commit()
        conexion.close()

        return redirect("/viajes")

    cursor.execute("""
    SELECT id, cliente, origen, destino, precio, combustible, camionero,
           comision, beneficio, estado, camionero_nombre, observaciones
    FROM viajes
    WHERE id=?
    """, (id,))

    viaje = cursor.fetchone()
    conexion.close()

    return render_template("editar_viaje.html", viaje=viaje)


@viajes_bp.route("/eliminar/<int:id>")
def eliminar_viaje(id):
    if CURRENT_ROLE != "MASTER":
        return redirect("/viajes")

    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM viajes WHERE id=?", (id,))
    conexion.commit()
    conexion.close()

    return redirect("/viajes")


@viajes_bp.route("/estado/<int:id>/<estado>")
def cambiar_estado(id, estado):
    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("UPDATE viajes SET estado=? WHERE id=?", (estado, id))

    if estado in ["Entregado", "Cancelado"]:
        cursor.execute("SELECT camionero_id FROM viajes WHERE id=?", (id,))
        resultado = cursor.fetchone()

        if resultado and resultado[0]:
            cursor.execute(
                "UPDATE camioneros SET estado='Disponible' WHERE id=?",
                (resultado[0],)
            )

    conexion.commit()
    conexion.close()

    return redirect("/viajes")