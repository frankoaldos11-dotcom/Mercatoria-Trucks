from flask import Flask, render_template, request, redirect, session
import sqlite3
from flask_bcrypt import Bcrypt

from routes.home import home_bp
from routes.dashboard import dashboard_bp
from routes.viajes import viajes_bp
from routes.camioneros import camioneros_bp
from routes.clientes import clientes_bp
from routes.cliente import cliente_bp

app = Flask(__name__)
app.secret_key = "mercatoria-super-secreto"
bcrypt = Bcrypt(app)


# -----------------------------
# BASE DE DATOS
# -----------------------------
def conectar():
    return sqlite3.connect("mercatoria.db")


def agregar_columna(cursor, tabla, columna, definicion):
    try:
        cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}")
    except:
        pass


def crear_base_datos():
    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        contacto TEXT,
        telefono TEXT,
        email TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS camioneros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        telefono TEXT,
        matricula TEXT,
        tipo TEXT,
        capacidad TEXT,
        estado TEXT DEFAULT 'Disponible'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS viajes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente TEXT,
        origen TEXT,
        destino TEXT,
        precio REAL,
        combustible REAL,
        camionero REAL,
        comision REAL,
        beneficio REAL
    )
    """)

    agregar_columna(cursor, "viajes", "estado", "TEXT DEFAULT 'Pendiente'")
    agregar_columna(cursor, "viajes", "camionero_id", "INTEGER")
    agregar_columna(cursor, "viajes", "camionero_nombre", "TEXT")
    agregar_columna(cursor, "viajes", "observaciones", "TEXT")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE,
        password TEXT,
        rol TEXT
    )
    """)

    cursor.execute("SELECT COUNT(*) FROM usuarios")
    total = cursor.fetchone()[0]
    if total == 0:
        hash_admin = bcrypt.generate_password_hash("1234").decode("utf-8")
        cursor.execute("""
        INSERT INTO usuarios (usuario, password, rol)
        VALUES (?, ?, ?)
        """, ("admin", hash_admin, "admin"))

    conexion.commit()
    conexion.close()


# -----------------------------
# PROTECCIÓN
# -----------------------------
def requiere_admin():
    return "usuario" in session and session.get("rol") == "admin"


# -----------------------------
# RUTAS PRINCIPALES
# -----------------------------
@app.route("/")
def home_publico():
    return render_template("home_publico.html")


@app.route("/dashboard")
def dashboard():
    if not requiere_admin():
        return redirect("/login")
    return render_template("dashboard.html")


@app.route("/cliente")
def cliente_home():
    if "usuario" not in session or session.get("rol") != "cliente":
        return redirect("/login")
    return render_template("cliente_inicio.html")


# -----------------------------
# LOGIN
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        password = request.form["password"]

        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT id, password, rol FROM usuarios WHERE usuario = ?", (usuario,))
        fila = cursor.fetchone()
        conexion.close()

        if fila:
            user_id, hash_guardado, rol = fila
            if bcrypt.check_password_hash(hash_guardado, password):
                session["usuario"] = usuario
                session["rol"] = rol
                session["user_id"] = user_id

                if rol == "admin":
                    return redirect("/dashboard")
                else:
                    return redirect("/cliente")

        return render_template("login.html", error="Credenciales incorrectas")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# -----------------------------
# REGISTRO PÚBLICO DE CLIENTES
# -----------------------------
@app.route("/registro", methods=["GET", "POST"])
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
        """, (email, hash_pw, "cliente"))

        cursor.execute("""
        INSERT INTO clientes (nombre, contacto, telefono, email)
        VALUES (?, ?, ?, ?)
        """, (nombre, nombre, telefono, email))

        conexion.commit()
        conexion.close()

        return redirect("/login")

    return render_template("registro.html")


# -----------------------------
# ENDPOINT OCULTO PARA TI
# -----------------------------
@app.route("/crear_usuario", methods=["GET", "POST"])
def crear_usuario():
    if request.method == "POST":
        usuario = request.form["usuario"]
        password = request.form["password"]
        rol = request.form["rol"]

        hash_pw = bcrypt.generate_password_hash(password).decode("utf-8")

        conexion = conectar()
        cursor = conexion.cursor()

        cursor.execute("""
        INSERT INTO usuarios (usuario, password, rol)
        VALUES (?, ?, ?)
        """, (usuario, hash_pw, rol))

        conexion.commit()
        conexion.close()

        return "Usuario creado correctamente"

    return """
    <form method='POST'>
        Usuario: <input name='usuario'><br>
        Password: <input name='password' type='password'><br>
        Rol: 
        <select name='rol'>
            <option value='cliente'>cliente</option>
            <option value='admin'>admin</option>
        </select><br>
        <button type='submit'>Crear</button>
    </form>
    """


# -----------------------------
# BLUEPRINTS
# -----------------------------
app.register_blueprint(home_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(viajes_bp)
app.register_blueprint(camioneros_bp)
app.register_blueprint(clientes_bp)
app.register_blueprint(cliente_bp)


# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    crear_base_datos()
    app.run(debug=True)
