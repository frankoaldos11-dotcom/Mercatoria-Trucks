from flask import Blueprint, render_template, request, redirect

from database import conectar


camioneros_bp = Blueprint("camioneros", __name__)


@camioneros_bp.route("/camioneros", methods=["GET", "POST"])
def camioneros():
    conexion = conectar()
    cursor = conexion.cursor()

    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        telefono = request.form["telefono"].strip()
        matricula = request.form["matricula"].strip()
        tipo = request.form["tipo"].strip()
        capacidad = request.form["capacidad"].strip()
        estado = request.form["estado"].strip()

        cursor.execute("""
        INSERT INTO camioneros
        (nombre, telefono, matricula, tipo, capacidad, estado)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (nombre, telefono, matricula, tipo, capacidad, estado))

        conexion.commit()

    cursor.execute("""
    SELECT id, nombre, telefono, matricula, tipo, capacidad, estado
    FROM camioneros
    ORDER BY id DESC
    """)
    camioneros_guardados = cursor.fetchall()

    cursor.execute("""
    SELECT id, cliente, origen, destino
    FROM viajes
    WHERE estado IN ('Solicitado', 'Asignado')
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

    cursor.execute("""
    SELECT nombre
    FROM camioneros
    WHERE id=? AND activo=1
    """, (camionero_id,))

    camionero = cursor.fetchone()

    if camionero:
        camionero_nombre = camionero[0]

        cursor.execute("""
        UPDATE viajes
        SET camionero_id=?,
            camionero_nombre=?,
            estado='Asignado',
            fecha_asignacion=CURRENT_TIMESTAMP
        WHERE id=?
        """, (camionero_id, camionero_nombre, viaje_id))

        cursor.execute("""
        UPDATE camioneros
        SET estado='Ocupado'
        WHERE id=?
        """, (camionero_id,))

    conexion.commit()
    conexion.close()

    return redirect("/viajes")