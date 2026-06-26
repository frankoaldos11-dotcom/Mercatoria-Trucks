from flask import Blueprint, render_template, request, redirect, session

from database import conectar
from services.finanzas_service import get_configuracion, guardar_configuracion

finanzas_bp = Blueprint("finanzas", __name__, url_prefix="/admin")


def solo_admin():
    return "usuario" in session and session.get("rol") == "admin"


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
            cur.execute(
                "INSERT OR REPLACE INTO configuracion_texto (clave, valor) VALUES (?, ?)",
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
    con.close()

    return render_template("admin/configuracion.html", config=config, config_texto=config_texto, mensaje=mensaje)
