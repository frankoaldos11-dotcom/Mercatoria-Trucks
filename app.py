import os
from datetime import timedelta
from flask import Flask, render_template, request, redirect, session
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
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-cambiar-en-produccion")
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)
app.config["WTF_CSRF_ENABLED"] = False

app.config["MAIL_SERVER"]         = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"]           = int(os.environ.get("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"]        = True
app.config["MAIL_USERNAME"]       = os.environ.get("MAIL_USERNAME", "")
app.config["MAIL_PASSWORD"]       = os.environ.get("MAIL_PASSWORD", "")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@mercatoriatruck.com")

bcrypt.init_app(app)
mail.init_app(app)
csrf = CSRFProtect(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)


@app.after_request
def set_security_headers(response):
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


@app.context_processor
def sidebar_badges():
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT COUNT(*) AS total FROM viajes WHERE estado IN ('Pendiente', 'Solicitado')"
        )
        viajes_urgentes = cursor.fetchone()["total"]
        cursor.execute(
            "SELECT COUNT(*) AS total FROM viajes WHERE estado = 'Solicitado'"
        )
        dashboard_urgentes = cursor.fetchone()["total"]
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
else:
    crear_base_datos(bcrypt)
    from migraciones import ejecutar_migraciones
    ejecutar_migraciones()


@app.route("/fix-viaje-tmp-borrar")
def fix_viaje():
    try:
        con = conectar()
        cur = con.cursor()
        cur.execute("SELECT id FROM usuarios WHERE usuario = 'juan@gmail.com'")
        u = cur.fetchone()
        if not u:
            return "Usuario no encontrado"
        cur.execute("SELECT id FROM clientes WHERE usuario_id = ?", (u["id"],))
        cl = cur.fetchone()
        if not cl:
            cur.execute("""
                INSERT INTO clientes (usuario_id, nombre, email, contacto, telefono)
                VALUES (?, 'juan', 'juan@gmail.com', 'juan', '')
            """, (u["id"],))
            con.commit()
            cur.execute("SELECT id FROM clientes WHERE usuario_id = ?", (u["id"],))
            cl = cur.fetchone()
        cur.execute("UPDATE viajes SET cliente_id = ? WHERE id = 1", (cl["id"],))
        con.commit()
        con.close()
        return f"OK — viaje #1 actualizado con cliente_id={cl['id']}"
    except Exception as e:
        return f"ERROR: {e}"


@app.route("/debug-viajes-tmp-borrar")
def debug_viajes():
    try:
        con = conectar()
        cur = con.cursor()
        cur.execute("SELECT id, cliente, cliente_id, origen, destino, estado FROM viajes ORDER BY id")
        filas = cur.fetchall()
        con.close()
        resultado = ""
        for f in filas:
            resultado += f"id={f['id']} cliente={f['cliente']} cliente_id={f['cliente_id']} origen={f['origen']} destino={f['destino']} estado={f['estado']}<br>"
        return resultado or "Sin viajes"
    except Exception as e:
        return f"ERROR: {e}"


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(debug=True)