from flask import Blueprint, render_template, request, redirect, session

from database import conectar
from db_config import ph
from services.finanzas_service import get_configuracion, guardar_configuracion
from routes.admin import registrar_auditoria

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
            "precio_litro_default",
        ]
        etiquetas = {
            "tarifa_km": "tarifa por km",
            "margen_combustible_divisor": "divisor combustible (reserva sin tipo de vehículo)",
            "multiplicador_pago_camionero": "multiplicador precio cliente",
            "minimo_km_garantizado": "km mínimo garantizado",
            "minimo_pago_usd": "pago mínimo al transportista",
            "comision_mercatoria_porcentaje": "comisión Mercatoria",
            "precio_litro_default": "precio/litro de reserva (zona sin precio)",
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
    cur.execute("SELECT id, nombre, descripcion, capacidad_ton, divisor_consumo FROM tipos_vehiculo WHERE activo = 1 ORDER BY nombre")
    tipos_vehiculo = cur.fetchall()
    cur.execute("SELECT id, origen, destino, zona, km_oficiales FROM rutas WHERE activa = 1 ORDER BY origen, destino")
    rutas = cur.fetchall()
    cur.execute("SELECT id, nombre, precio_litro FROM zonas_combustible WHERE activo = 1 ORDER BY nombre")
    zonas_combustible = cur.fetchall()
    con.close()

    return render_template(
        "admin/configuracion.html",
        config=config,
        config_texto=config_texto,
        mensaje=mensaje,
        hubo_errores=hubo_errores,
        tipos_vehiculo=tipos_vehiculo,
        rutas=rutas,
        zonas_combustible=zonas_combustible,
    )


@finanzas_bp.route("/configuracion/tipo-vehiculo/nuevo", methods=["POST"])
def nuevo_tipo_vehiculo_config():
    if not solo_admin():
        return redirect("/login")
    nombre = request.form.get("nombre", "").strip()
    descripcion = request.form.get("descripcion", "").strip()
    capacidad_ton = request.form.get("capacidad_ton", "").strip()
    divisor_consumo = request.form.get("divisor_consumo", "").strip()
    if nombre:
        con = conectar()
        cur = con.cursor()
        try:
            cur.execute(
                "INSERT INTO tipos_vehiculo (nombre, descripcion, capacidad_ton, divisor_consumo, activo) VALUES (?, ?, ?, ?, 1)",
                (
                    nombre, descripcion or None,
                    float(capacidad_ton) if capacidad_ton else None,
                    float(divisor_consumo) if divisor_consumo else 2.0,
                )
            )
            registrar_auditoria(cur, f"Creó tipo de vehículo {nombre}", "Configuración", "tipo_vehiculo")
            con.commit()
        except Exception:
            pass
        con.close()
    return redirect("/admin/configuracion?ok_tipo=1")


@finanzas_bp.route("/configuracion/tipo-vehiculo/<int:id>/divisor", methods=["POST"])
def editar_divisor_tipo_vehiculo_config(id):
    if not solo_admin():
        return redirect("/login")
    divisor = request.form.get("divisor_consumo", "").strip()
    con = conectar()
    cur = con.cursor()
    try:
        valor = float(divisor) if divisor else 2.0
        cur.execute(f"UPDATE tipos_vehiculo SET divisor_consumo = {ph()} WHERE id = {ph()}", (valor, id))
        registrar_auditoria(cur, f"Actualizó divisor de consumo a {valor}", "Configuración", "tipo_vehiculo", id)
        con.commit()
    except (ValueError, TypeError):
        pass
    con.close()
    return redirect("/admin/configuracion?tab=tab-tipos")


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


@finanzas_bp.route("/configuracion/zona-combustible/nuevo", methods=["POST"])
def nueva_zona_combustible_config():
    if not solo_admin():
        return redirect("/login")
    nombre = request.form.get("nombre", "").strip()
    precio_litro = request.form.get("precio_litro", "").strip()
    if nombre and precio_litro:
        con = conectar()
        cur = con.cursor()
        try:
            valor = float(precio_litro)
            cur.execute(
                f"INSERT INTO zonas_combustible (nombre, precio_litro, activo) VALUES ({ph()}, {ph()}, 1)",
                (nombre, valor)
            )
            registrar_auditoria(cur, f"Creó zona de combustible {nombre} (${valor}/L)", "Configuración", "zona_combustible")
            con.commit()
        except (ValueError, TypeError):
            pass
        con.close()
    return redirect("/admin/configuracion?ok_zona=1&tab=tab-zonas")


@finanzas_bp.route("/configuracion/zona-combustible/<int:id>/precio", methods=["POST"])
def editar_precio_zona_combustible_config(id):
    if not solo_admin():
        return redirect("/login")
    precio_litro = request.form.get("precio_litro", "").strip()
    con = conectar()
    cur = con.cursor()
    try:
        valor = float(precio_litro)
        cur.execute(f"UPDATE zonas_combustible SET precio_litro = {ph()} WHERE id = {ph()}", (valor, id))
        registrar_auditoria(cur, f"Actualizó precio de zona de combustible a ${valor}/L", "Configuración", "zona_combustible", id)
        con.commit()
    except (ValueError, TypeError):
        pass
    con.close()
    return redirect("/admin/configuracion?tab=tab-zonas")


@finanzas_bp.route("/configuracion/zona-combustible/<int:id>/eliminar", methods=["POST"])
def eliminar_zona_combustible_config(id):
    if not solo_admin():
        return redirect("/login")
    con = conectar()
    cur = con.cursor()
    cur.execute(f"UPDATE zonas_combustible SET activo = 0 WHERE id = {ph()}", (id,))
    registrar_auditoria(cur, "Eliminó zona de combustible", "Configuración", "zona_combustible", id)
    con.commit()
    con.close()
    return redirect("/admin/configuracion?tab=tab-zonas")
