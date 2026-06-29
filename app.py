import os
import time
import logging
from datetime import timedelta
from flask import Flask, render_template, request, redirect, session, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

from extensions import bcrypt, mail
from database import conectar, crear_base_datos
from db_config import USE_POSTGRES
from utils.constants import ROLES

from routes.home import home_bp
from routes.dashboard import dashboard_bp
from routes.viajes import viajes_bp
from routes.camioneros import camioneros_bp
from routes.clientes import clientes_bp
from routes.cliente import cliente_bp
from routes.admin import admin_bp
from routes.vehiculos import vehiculos_bp
from routes.comercial import comercial_bp
from routes.finanzas import finanzas_bp


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
if not app.config["SECRET_KEY"]:
    raise RuntimeError("SECRET_KEY no configurada — define la variable de entorno SECRET_KEY")
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)
app.config["WTF_CSRF_ENABLED"] = True

app.config["MAIL_SERVER"]         = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"]           = int(os.environ.get("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"]        = True
app.config["MAIL_USERNAME"]       = os.environ.get("MAIL_USERNAME", "")
app.config["MAIL_PASSWORD"]       = os.environ.get("MAIL_PASSWORD", "")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@mercatoriatruck.com")

bcrypt.init_app(app)
mail.init_app(app)

def fmt_fecha(value, fmt='%Y-%m-%d %H:%M'):
    if not value:
        return '—'
    if hasattr(value, 'strftime'):
        return value.strftime(fmt)
    try:
        from datetime import datetime
        return datetime.strptime(str(value)[:16], '%Y-%m-%d %H:%M').strftime(fmt)
    except Exception:
        return str(value)[:16]

app.jinja_env.filters['fmt_fecha'] = fmt_fecha

csrf = CSRFProtect(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)


@app.before_request
def _record_start_time():
    g.start_time = time.monotonic()


@app.before_request
def _validate_session_role():
    """Re-valida el rol del usuario en BD para prevenir drift por cookies compartidas."""
    if "user_id" not in session or "rol" not in session:
        return
    try:
        con = conectar()
        cur = con.cursor()
        cur.execute("SELECT rol, activo FROM usuarios WHERE id = ?", (session["user_id"],))
        row = cur.fetchone()
        con.close()
        if not row or not row["activo"]:
            session.clear()
            return
        if row["rol"] != session["rol"]:
            session["rol"] = row["rol"]
    except Exception:
        pass


@app.after_request
def set_security_headers(response):
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    if app.debug:
        ms = (time.monotonic() - getattr(g, "start_time", time.monotonic())) * 1000
        app.logger.debug("[%s] %s %.1fms", request.method, request.path, ms)
    return response


@app.context_processor
def sidebar_badges():
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT
                COUNT(*) AS urgentes,
                COUNT(CASE WHEN estado = 'Solicitado' THEN 1 END) AS solicitados
            FROM viajes
            WHERE estado IN ('Pendiente', 'Solicitado')
        """)
        row = cursor.fetchone()
        viajes_urgentes    = row["urgentes"]    if row else 0
        dashboard_urgentes = row["solicitados"] if row else 0
        conexion.close()
    except Exception:
        viajes_urgentes = 0
        dashboard_urgentes = 0
    return dict(
        sidebar_viajes_urgentes=viajes_urgentes,
        sidebar_dashboard_urgentes=dashboard_urgentes,
    )


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if request.method == "POST":
        usuario = request.form["usuario"].strip().lower()
        password = request.form["password"]

        conexion = conectar()
        cursor = conexion.cursor()

        cursor.execute("""
        SELECT id, password, rol
        FROM usuarios
        WHERE usuario = ?
        """, (usuario,))

        fila = cursor.fetchone()
        conexion.close()

        if fila:
            user_id = fila["id"]
            hash_guardado = fila["password"]
            rol = fila["rol"]

            if bcrypt.check_password_hash(hash_guardado, password):
                session.permanent = True
                session["usuario"] = usuario
                session["rol"] = rol
                session["user_id"] = user_id

                if rol in [ROLES["ADMIN"], ROLES["OPERADOR"]]:
                    return redirect("/admin")

                if rol == ROLES["CLIENTE"]:
                    return redirect("/cliente")

        return render_template("login.html", error="Credenciales incorrectas")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/registro")
def registro_redirect():
    return redirect("/cliente/registro")


@app.route("/registro_legacy", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        telefono = request.form["telefono"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        confirmar = request.form["confirmar"]

        if email == "":
            return render_template("registro.html", error="El correo no puede estar vacío")

        if password != confirmar:
            return render_template("registro.html", error="Las contraseñas no coinciden")

        conexion = conectar()
        cursor = conexion.cursor()

        cursor.execute("SELECT id FROM usuarios WHERE usuario = ?", (email,))
        existe = cursor.fetchone()

        if existe:
            conexion.close()
            return render_template("registro.html", error="Este correo ya está registrado")

        hash_pw = bcrypt.generate_password_hash(password).decode("utf-8")

        cursor.execute("""
        INSERT INTO usuarios (usuario, password, rol)
        VALUES (?, ?, ?)
        """, (email, hash_pw, ROLES["CLIENTE"]))

        cursor.execute("""
        INSERT INTO clientes (nombre, contacto, telefono, email)
        VALUES (?, ?, ?, ?)
        """, (nombre, nombre, telefono, email))

        conexion.commit()
        conexion.close()

        return redirect("/login")

    return render_template("registro.html")


app.register_blueprint(home_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(viajes_bp)
app.register_blueprint(camioneros_bp)
app.register_blueprint(clientes_bp)
app.register_blueprint(cliente_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(vehiculos_bp)
app.register_blueprint(comercial_bp)
app.register_blueprint(finanzas_bp)

if USE_POSTGRES:
    from migraciones_pg import ejecutar_migraciones_pg
    ejecutar_migraciones_pg()
    # Migraciones v1.1: corre siempre, ignora SKIP_MIGRATIONS
    with app.app_context():
        from migrations_v11 import aplicar_migraciones_v11
        aplicar_migraciones_v11()
        from migrations_v12 import aplicar_migraciones_v12
        aplicar_migraciones_v12()
else:
    crear_base_datos(bcrypt)
    from migraciones import ejecutar_migraciones
    ejecutar_migraciones()


@app.route("/sw.js")
def service_worker():
    response = app.send_static_file("sw.js")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Content-Type"] = "application/javascript"
    return response


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(debug=True)