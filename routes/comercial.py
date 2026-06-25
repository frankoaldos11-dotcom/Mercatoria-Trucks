from flask import Blueprint, render_template, request, redirect, jsonify, session
import sqlite3

from routes.admin import requiere_admin

from services.comercial_service import (
    get_all_rutas,
    get_ruta,
    crear_ruta,
    ruta_existe,
    get_all_tipos_vehiculo,
    crear_tipo_vehiculo,
    get_all_tarifas,
    crear_tarifa,
    cotizar,
    guardar_cotizacion,
    get_all_cotizaciones,
    get_cotizacion_detalle,
    convertir_cotizacion_en_viaje
)

comercial_bp = Blueprint("comercial", __name__)


def conectar_comercial():
    conexion = sqlite3.connect("mercatoria.db")
    conexion.row_factory = sqlite3.Row
    return conexion


def get_viaje_id_por_cotizacion(cotizacion_id):
    conexion = conectar_comercial()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT id
        FROM viajes
        WHERE cotizacion_id = ?
        ORDER BY id DESC
        LIMIT 1
    """, (cotizacion_id,))

    viaje = cursor.fetchone()
    conexion.close()

    return viaje["id"] if viaje else None


@comercial_bp.route("/admin/comercial/rutas")
def rutas():
    if not requiere_admin():
        return redirect("/login")
    return render_template("admin/comercial/rutas.html", rutas=get_all_rutas())


@comercial_bp.route("/admin/comercial/rutas/nueva", methods=["POST"])
def nueva_ruta():
    if not requiere_admin():
        return redirect("/login")

    origen = request.form["origen"]
    destino = request.form["destino"]
    zona = request.form.get("zona", "")
    km = request.form["km"]

    if not ruta_existe(origen, destino):
        crear_ruta(origen, destino, zona, km)

    return redirect("/admin/comercial/rutas")


@comercial_bp.route("/admin/comercial/vehiculos")
def tipos_vehiculo():
    if not requiere_admin():
        return redirect("/login")

    return render_template(
        "admin/comercial/tipos_vehiculo.html",
        tipos=get_all_tipos_vehiculo()
    )


@comercial_bp.route("/admin/comercial/vehiculos/nuevo", methods=["POST"])
def nuevo_tipo_vehiculo():
    if not requiere_admin():
        return redirect("/login")

    nombre = request.form["nombre"]
    descripcion = request.form.get("descripcion", "")
    capacidad = request.form.get("capacidad_ton", "")

    crear_tipo_vehiculo(nombre, descripcion, capacidad)

    return redirect("/admin/comercial/vehiculos")


@comercial_bp.route("/admin/comercial/tarifas")
def tarifas():
    if not requiere_admin():
        return redirect("/login")

    return render_template(
        "admin/comercial/tarifas.html",
        tarifas=get_all_tarifas(),
        rutas=get_all_rutas(),
        tipos=get_all_tipos_vehiculo()
    )


@comercial_bp.route("/admin/comercial/tarifas/nueva", methods=["POST"])
def nueva_tarifa():
    if not requiere_admin():
        return redirect("/login")

    crear_tarifa(
        ruta_id=request.form["ruta_id"],
        tipo_vehiculo_id=request.form["tipo_vehiculo_id"],
        precio_cliente=request.form["precio_cliente"],
        pago_camionero=request.form["pago_camionero"],
        combustible_estimado=request.form.get("combustible_estimado", ""),
        vigencia_desde=request.form.get("vigencia_desde", ""),
        vigencia_hasta=request.form.get("vigencia_hasta", ""),
    )

    return redirect("/admin/comercial/tarifas")


@comercial_bp.route("/admin/comercial/cotizar")
def cotizar_view():
    if not requiere_admin():
        return redirect("/login")

    from routes.clientes import get_all_clientes

    return render_template(
        "admin/comercial/cotizar.html",
        rutas=get_all_rutas(),
        tipos=get_all_tipos_vehiculo(),
        clientes=get_all_clientes()
    )


@comercial_bp.route("/admin/comercial/cotizar/calcular", methods=["POST"])
def calcular_cotizacion():
    if not requiere_admin():
        return redirect("/login")

    ruta_id = request.form["ruta_id"]
    tipo_vehiculo_id = request.form["tipo_vehiculo_id"]

    resultado = cotizar(ruta_id, tipo_vehiculo_id)

    if not resultado:
        return jsonify({"error": "No existe tarifa para esa combinación"}), 404

    return jsonify(resultado)


@comercial_bp.route("/admin/comercial/cotizar/guardar", methods=["POST"])
def guardar_cotizacion_view():
    if not requiere_admin():
        return redirect("/login")

    ruta_id = request.form["ruta_id"]
    tipo_vehiculo_id = request.form["tipo_vehiculo_id"]
    cliente_id = request.form.get("cliente_id")
    precio_override = request.form.get("precio_final")
    motivo = request.form.get("motivo")

    datos = cotizar(ruta_id, tipo_vehiculo_id)

    if not datos:
        return redirect("/admin/comercial/cotizar")

    guardar_cotizacion(
        datos,
        cliente_id if cliente_id else None,
        session["user_id"],
        precio_override,
        motivo
    )

    return redirect("/admin/comercial/cotizaciones")


@comercial_bp.route("/admin/comercial/cotizaciones")
def cotizaciones():
    if not requiere_admin():
        return redirect("/login")

    return render_template(
        "admin/comercial/cotizaciones.html",
        cotizaciones=get_all_cotizaciones()
    )


@comercial_bp.route("/admin/comercial/cotizacion/<int:id>")
def ver_cotizacion(id):
    if not requiere_admin():
        return redirect("/login")

    cotizacion = get_cotizacion_detalle(id)

    if not cotizacion:
        return redirect("/admin/comercial/cotizaciones")

    viaje_id = get_viaje_id_por_cotizacion(id)

    return render_template(
        "admin/comercial/cotizacion_detalle.html",
        cotizacion=cotizacion,
        viaje_id=viaje_id
    )


@comercial_bp.route("/admin/comercial/cotizacion/<int:id>/convertir", methods=["POST"])
def convertir_cotizacion(id):
    if not requiere_admin():
        return redirect("/login")

    viaje_id = convertir_cotizacion_en_viaje(id)

    if not viaje_id:
        return redirect(f"/admin/comercial/cotizacion/{id}")

    return redirect(f"/admin/viajes/{viaje_id}/gestionar")