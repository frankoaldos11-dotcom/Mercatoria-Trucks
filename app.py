from datetime import timedelta
from flask import Flask, render_template, request, redirect, session

from extensions import bcrypt
from database import conectar, crear_base_datos
from migraciones import ejecutar_migraciones
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
app.secret_key = "mercatoria-super-secreto"
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)

bcrypt.init_app(app)


@app.context_processor
def sidebar_badges():
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM viajes WHERE estado IN ('Pendiente', 'Solicitado')"
        )
        viajes_urgentes = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM viajes WHERE estado = 'Solicitado'"
        )
        dashboard_urgentes = cursor.fetchone()[0]
        conexion.close()
    except Exception:
        viajes_urgentes = 0
        dashboard_urgentes = 0
    return dict(
        sidebar_viajes_urgentes=viajes_urgentes,
        sidebar_dashboard_urgentes=dashboard_urgentes,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"].strip()
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
            user_id, hash_guardado, rol = fila

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

crear_base_datos(bcrypt)
ejecutar_migraciones()


if __name__ == "__main__":
    app.run(debug=True)