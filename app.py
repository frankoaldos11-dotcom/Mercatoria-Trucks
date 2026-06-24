from flask import Flask, render_template, request, redirect
import sqlite3

from routes.home import home_bp
from routes.dashboard import dashboard_bp
from routes.viajes import viajes_bp
from routes.camioneros import camioneros_bp
from routes.clientes import clientes_bp
from routes.cliente import cliente_bp

app = Flask(__name__)


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

    conexion.commit()
    conexion.close()


# -----------------------------
# RUTAS PRINCIPALES
# -----------------------------
@app.route("/")
def home_publico():
    return render_template("home_publico.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/cliente")
def cliente_home():
    return render_template("cliente_inicio.html")


# -----------------------------
# LOGIN
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        password = request.form["password"]

        # Login simple
        if usuario == "admin" and password == "1234":
            return redirect("/dashboard")
        else:
            return render_template("login.html", error="Credenciales incorrectas")

    return render_template("login.html")


@app.route("/logout")
def logout():
    return redirect("/login")


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
