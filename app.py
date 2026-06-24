from flask import Flask
import sqlite3

from routes.home import home_bp
from routes.dashboard import dashboard_bp
from routes.viajes import viajes_bp
from routes.camioneros import camioneros_bp
from routes.clientes import clientes_bp
from routes.cliente import cliente_bp   # ← AQUI

app = Flask(__name__)


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


# BLUEPRINTS
app.register_blueprint(home_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(viajes_bp)
app.register_blueprint(camioneros_bp)
app.register_blueprint(clientes_bp)
app.register_blueprint(cliente_bp)   # ← AQUI


if __name__ == "__main__":
    crear_base_datos()
    app.run(debug=True)
