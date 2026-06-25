from flask import Blueprint, redirect

from database import conectar

camioneros_bp = Blueprint("camioneros", __name__)


@camioneros_bp.route("/camioneros", methods=["GET", "POST"])
def camioneros():
    return redirect("/admin/camioneros")


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

    return redirect("/admin/viajes")
