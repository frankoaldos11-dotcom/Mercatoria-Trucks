import sqlite3

DATABASE_NAME = "mercatoria.db"


def conectar():
    return sqlite3.connect(DATABASE_NAME)


def agregar_columna(cursor, tabla, columna, definicion):
    try:
        cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}")
    except sqlite3.OperationalError:
        pass


def crear_base_datos(bcrypt):
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
        precio REAL DEFAULT 0,
        combustible REAL DEFAULT 0,
        camionero REAL DEFAULT 0,
        comision REAL DEFAULT 0,
        beneficio REAL DEFAULT 0,
        estado TEXT DEFAULT 'Solicitado',
        camionero_id INTEGER,
        camionero_nombre TEXT,
        observaciones TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE,
        password TEXT,
        rol TEXT
    )
    """)

    agregar_columna(cursor, "viajes", "estado", "TEXT DEFAULT 'Solicitado'")
    agregar_columna(cursor, "viajes", "camionero_id", "INTEGER")
    agregar_columna(cursor, "viajes", "camionero_nombre", "TEXT")
    agregar_columna(cursor, "viajes", "observaciones", "TEXT")

    cursor.execute("SELECT id FROM usuarios WHERE usuario = ?", ("admin",))
    admin_existe = cursor.fetchone()

    if not admin_existe:
        hash_admin = bcrypt.generate_password_hash("1234").decode("utf-8")

        cursor.execute("""
        INSERT INTO usuarios (usuario, password, rol)
        VALUES (?, ?, ?)
        """, ("admin", hash_admin, "admin"))

    conexion.commit()
    conexion.close()