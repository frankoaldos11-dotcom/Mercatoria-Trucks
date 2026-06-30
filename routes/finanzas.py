from flask import Blueprint, render_template, request, redirect, session

from database import conectar
from db_config import USE_POSTGRES
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

    if request.method == "POST":
        claves = [
            "tarifa_km",
            "margen_combustible_divisor",
            "multiplicador_pago_camionero",
            "minimo_km_garantizado",
            "minimo_pago_usd",
            "comision_mercatoria_porcentaje",
        ]
        parametros = {}
        for clave in claves:
            try:
                parametros[clave] = float(request.form[clave])
            except (KeyError, ValueError):
                pass
        guardar_configuracion(parametros)

        claves_texto = ["mail_username", "mail_password"]
        con = conectar()
        cur = con.cursor()
        for clave in claves_texto:
            valor = request.form.get(clave, "").strip()
            if USE_POSTGRES:
                cur.execute(
                    "INSERT INTO configuracion_texto (clave, valor) VALUES (%s, %s) "
                    "ON CONFLICT (clave) DO UPDATE SET valor = EXCLUDED.valor",
                    (clave, valor)
                )
            else:
                cur.execute(
                    "INSERT INTO configuracion_texto (clave, valor) VALUES (?, ?) "
                    "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
                    (clave, valor)
                )
        con.commit()
        con.close()

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
