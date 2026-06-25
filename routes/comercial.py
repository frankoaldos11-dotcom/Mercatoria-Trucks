from flask import Blueprint, render_template, request, redirect, session, jsonify
from services.comercial_service import (
    get_all_rutas, crear_ruta, ruta_existe,
    get_all_tipos_vehiculo, crear_tipo_vehiculo,
    get_all_tarifas, crear_tarifa,
    cotizar, guardar_cotizacion
)

comercial_bp = Blueprint("comercial", __name__)


def require_admin(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("rol") not in ["admin", "operador"]:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated


# ── RUTAS ────────────────────────────────────────────────────────────────────

@comercial_bp.route("/admin/comercial/rutas")
@require_admin
def rutas():
    return render_template("admin/comercial/rutas.html", rutas=get_all_rutas())


@comercial_bp.route("/admin/comercial/rutas/nueva", methods=["POST"])
@require_admin
def nueva_ruta():
    origen  = request.form["origen"]
    destino = request.form["destino"]
    zona    = request.form.get("zona", "")
    km      = request.form["km"]

    if not ruta_existe(origen, destino):
        crear_ruta(origen, destino, zona, km)

    return redirect("/admin/comercial/rutas")


# ── TIPOS DE VEHÍCULO ────────────────────────────────────────────────────────

@comercial_bp.route("/admin/comercial/vehiculos")
@require_admin
def tipos_vehiculo():
    return render_template("admin/comercial/tipos_vehiculo.html",
                           tipos=get_all_tipos_vehiculo())


@comercial_bp.route("/admin/comercial/vehiculos/nuevo", methods=["POST"])
@require_admin
def nuevo_tipo_vehiculo():
    nombre      = request.form["nombre"]
    descripcion = request.form.get("descripcion", "")
    capacidad   = request.form.get("capacidad_ton", "")
    crear_tipo_vehiculo(nombre, descripcion, capacidad)
    return redirect("/admin/comercial/vehiculos")


# ── TARIFAS ──────────────────────────────────────────────────────────────────

@comercial_bp.route("/admin/comercial/tarifas")
@require_admin
def tarifas():
    return render_template("admin/comercial/tarifas.html",
                           tarifas=get_all_tarifas(),
                           rutas=get_all_rutas(),
                           tipos=get_all_tipos_vehiculo())


@comercial_bp.route("/admin/comercial/tarifas/nueva", methods=["POST"])
@require_admin
def nueva_tarifa():
    crear_tarifa(
        ruta_id           = request.form["ruta_id"],
        tipo_vehiculo_id  = request.form["tipo_vehiculo_id"],
        precio_cliente    = request.form["precio_cliente"],
        pago_camionero    = request.form["pago_camionero"],
        combustible_estimado = request.form.get("combustible_estimado", ""),
        vigencia_desde    = request.form.get("vigencia_desde", ""),
        vigencia_hasta    = request.form.get("vigencia_hasta", ""),
    )
    return redirect("/admin/comercial/tarifas")


# ── COTIZACIÓN ───────────────────────────────────────────────────────────────

@comercial_bp.route("/admin/comercial/cotizar")
@require_admin
def cotizar_view():
    from routes.clientes import get_all_clientes  # evitar import circular
    return render_template("admin/comercial/cotizar.html",
                           rutas=get_all_rutas(),
                           tipos=get_all_tipos_vehiculo(),
                           clientes=get_all_clientes())


@comercial_bp.route("/admin/comercial/cotizar/calcular", methods=["POST"])
@require_admin
def calcular_cotizacion():
    ruta_id          = request.form["ruta_id"]
    tipo_vehiculo_id = request.form["tipo_vehiculo_id"]
    resultado = cotizar(ruta_id, tipo_vehiculo_id)
    if not resultado:
        return jsonify({"error": "No existe tarifa para esa combinación"}), 404
    return jsonify(resultado)


@comercial_bp.route("/admin/comercial/cotizar/guardar", methods=["POST"])
@require_admin
def guardar_cotizacion_view():
    ruta_id          = request.form["ruta_id"]
    tipo_vehiculo_id = request.form["tipo_vehiculo_id"]
    cliente_id       = request.form.get("cliente_id")
    precio_override  = request.form.get("precio_final")
    motivo           = request.form.get("motivo")

    datos = cotizar(ruta_id, tipo_vehiculo_id)
    if not datos:
        return redirect("/admin/comercial/cotizar")

    guardar_cotizacion(datos, cliente_id, session["user_id"], precio_override, motivo)
    return redirect("/admin/comercial/tarifas")