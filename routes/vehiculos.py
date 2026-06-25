from flask import Blueprint, render_template, request, redirect

from database import conectar


vehiculos_bp = Blueprint("vehiculos", __name__)


@vehiculos_bp.route("/vehiculos", methods=["GET", "POST"])
def vehiculos():
    conexion = conectar()
    cursor = conexion.cursor()

    if request.method == "POST":
        camionero_id = request.form.get("camionero_id") or None
        matricula = request.form["matricula"].strip()
        marca = request.form.get("marca", "").strip()
        modelo = request.form.get("modelo", "").strip()
        tipo = request.form["tipo"].strip()
        capacidad = request.form["capacidad"].strip()
        combustible = request.form["combustible"].strip()
        estado = request.form["estado"].strip()

        cursor.execute("""
            INSERT INTO vehiculos
            (camionero_id, matricula, marca, modelo, tipo, capacidad, combustible, estado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            camionero_id,
            matricula,
            marca,
            modelo,
            tipo,
            capacidad,
            combustible,
            estado
        ))

        conexion.commit()

        return redirect("/vehiculos")

    cursor.execute("""
        SELECT id, nombre
        FROM camioneros
        WHERE activo = 1
        ORDER BY nombre ASC
    """)
    camioneros = cursor.fetchall()

    cursor.execute("""
        SELECT nombre
        FROM tipos_vehiculo
        WHERE activo = 1
        ORDER BY nombre ASC
    """)
    tipos_vehiculo = cursor.fetchall()

    cursor.execute("""
        SELECT
            v.id,
            v.matricula,
            v.marca,
            v.modelo,
            v.tipo,
            v.capacidad,
            v.combustible,
            v.estado,
            c.nombre
        FROM vehiculos v
        LEFT JOIN camioneros c ON c.id = v.camionero_id
        WHERE v.activo = 1
        ORDER BY v.id DESC
    """)
    vehiculos_guardados = cursor.fetchall()

    conexion.close()

    return render_template(
        "vehiculos.html",
        vehiculos=vehiculos_guardados,
        camioneros=camioneros,
        tipos_vehiculo=tipos_vehiculo
    )