from flask import Blueprint, render_template, request, redirect, session

from database import conectar
from db_config import ph
from services.finanzas_service import get_configuracion, guardar_configuracion

finanzas_bp = Blueprint("finanzas", __name__, url_prefix="/admin")


def solo_admin():
    return "usuario" in session and session.get("rol") == "admin"


def _requiere_admin_o_operador():
    return "usuario" in session and session.get("rol") in ["admin", "operador"]


@finanzas_bp.route("/configuracion", methods=["GET", "POST"])
def configuracion():
    if not solo_admin():
        return redirect("/login")

    mensaje = None
    hubo_errores = False

    if request.method == "POST":
        claves = [
            "tarifa_km",
            "margen_combustible_divisor",
            "multiplicador_pago_camionero",
            "minimo_km_garantizado",
            "minimo_pago_usd",
            "comision_mercatoria_porcentaje",
        ]
        etiquetas = {
            "tarifa_km": "tarifa por km",
            "margen_combustible_divisor": "divisor combustible",
            "multiplicador_pago_camionero": "multiplicador precio cliente",
            "minimo_km_garantizado": "km mínimo garantizado",
            "minimo_pago_usd": "pago mínimo al camionero",
            "comision_mercatoria_porcentaje": "comisión Mercatoria",
        }
        parametros = {}
        errores_parametros = []
        for clave in claves:
            try:
                parametros[clave] = float(request.form[clave])
            except (KeyError, ValueError):
                errores_parametros.append(etiquetas[clave])
        guardar_configuracion(parametros)

        claves_texto = ["mail_username", "mail_password"]
        con = conectar()
        cur = con.cursor()
        for clave in claves_texto:
            valor = request.form.get(clave, "").strip()
            cur.execute(
                f"INSERT INTO configuracion_texto (clave, valor) VALUES ({ph()}, {ph()}) "
                "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
                (clave, valor)
            )
        con.commit()
        con.close()

        if errores_parametros:
            hubo_errores = True
            mensaje = "Se guardaron los parámetros, excepto: " + ", ".join(
                f"{nombre} (valor no válido)" for nombre in errores_parametros
            ) + "."
        else:
            mensaje = "Configuración guardada correctamente."

    config = get_configuracion()

    con = conectar()
    cur = con.cursor()
    cur.execute("SELECT clave, valor FROM configuracion_texto")
    config_texto = {r["clave"]: r["valor"] for r in cur.fetchall()}
    cur.execute("SELECT id, nombre, descripcion, capacidad_ton FROM tipos_vehiculo WHERE activo = 1 ORDER BY nombre")
    tipos_vehiculo = cur.fetchall()
    cur.execute("SELECT id, origen, destino, zona, km_oficiales FROM rutas WHERE activa = 1 ORDER BY origen, destino")
    rutas = cur.fetchall()
    con.close()

    return render_template(
        "admin/configuracion.html",
        config=config,
        config_texto=config_texto,
        mensaje=mensaje,
        hubo_errores=hubo_errores,
        tipos_vehiculo=tipos_vehiculo,
        rutas=rutas,
    )


@finanzas_bp.route("/configuracion/tipo-vehiculo/nuevo", methods=["POST"])
def nuevo_tipo_vehiculo_config():
    if not solo_admin():
        return redirect("/login")
    nombre = request.form.get("nombre", "").strip()
    descripcion = request.form.get("descripcion", "").strip()
    capacidad_ton = request.form.get("capacidad_ton", "").strip()
    if nombre:
        con = conectar()
        cur = con.cursor()
        try:
            cur.execute(
                "INSERT INTO tipos_vehiculo (nombre, descripcion, capacidad_ton, activo) VALUES (?, ?, ?, 1)",
                (nombre, descripcion or None, float(capacidad_ton) if capacidad_ton else None)
            )
            con.commit()
        except Exception:
            pass
        con.close()
    return redirect("/admin/configuracion?ok_tipo=1")


@finanzas_bp.route("/configuracion/ruta/<int:id>/km", methods=["POST"])
def editar_km_ruta_config(id):
    if not solo_admin():
        return redirect("/login")
    km = request.form.get("km_oficiales", "").strip()
    con = conectar()
    cur = con.cursor()
    try:
        cur.execute(
            "UPDATE rutas SET km_oficiales = ? WHERE id = ?",
            (float(km) if km else None, id)
        )
        con.commit()
    except (ValueError, TypeError):
        pass
    con.close()
    return redirect("/admin/configuracion?tab=tab-rutas")


@finanzas_bp.route("/configuracion/tipo-vehiculo/<int:id>/eliminar", methods=["POST"])
def eliminar_tipo_vehiculo_config(id):
    if not solo_admin():
        return redirect("/login")
    con = conectar()
    cur = con.cursor()
    cur.execute("UPDATE tipos_vehiculo SET activo = 0 WHERE id = ?", (id,))
    con.commit()
    con.close()
    return redirect("/admin/configuracion")
