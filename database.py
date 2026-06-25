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
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE,
        password TEXT,
        rol TEXT,
        activo INTEGER DEFAULT 1,
        fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        nombre TEXT,
        empresa TEXT,
        contacto TEXT,
        telefono TEXT,
        email TEXT,
        direccion TEXT,
        activo INTEGER DEFAULT 1,
        fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS camioneros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        telefono TEXT,
        licencia TEXT,
        matricula TEXT,
        tipo TEXT,
        capacidad TEXT,
        estado TEXT DEFAULT 'Disponible',
        activo INTEGER DEFAULT 1,
        fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehiculos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        camionero_id INTEGER,
        matricula TEXT,
        marca TEXT,
        modelo TEXT,
        tipo TEXT,
        capacidad TEXT,
        combustible TEXT,
        estado TEXT DEFAULT 'Disponible',
        activo INTEGER DEFAULT 1,
        fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS viajes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        cliente TEXT,
        cliente_id INTEGER,

        origen TEXT,
        destino TEXT,

        precio REAL DEFAULT 0,
        combustible REAL DEFAULT 0,
        pago_camionero REAL DEFAULT 0,
        camionero REAL DEFAULT 0,
        comision REAL DEFAULT 0,
        beneficio REAL DEFAULT 0,

        estado TEXT DEFAULT 'Solicitado',

        camionero_id INTEGER,
        camionero_nombre TEXT,
        vehiculo_id INTEGER,

        fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
        fecha_asignacion TEXT,
        fecha_recogida TEXT,
        fecha_entrega TEXT,

        observaciones TEXT
    )
    """)

    # Compatibilidad con bases existentes
    agregar_columna(cursor, "usuarios", "activo", "INTEGER DEFAULT 1")
    agregar_columna(cursor, "usuarios", "fecha_creacion", "TEXT DEFAULT CURRENT_TIMESTAMP")

    agregar_columna(cursor, "clientes", "usuario_id", "INTEGER")
    agregar_columna(cursor, "clientes", "empresa", "TEXT")
    agregar_columna(cursor, "clientes", "direccion", "TEXT")
    agregar_columna(cursor, "clientes", "activo", "INTEGER DEFAULT 1")
    agregar_columna(cursor, "clientes", "fecha_creacion", "TEXT DEFAULT CURRENT_TIMESTAMP")

    agregar_columna(cursor, "camioneros", "licencia", "TEXT")
    agregar_columna(cursor, "camioneros", "activo", "INTEGER DEFAULT 1")
    agregar_columna(cursor, "camioneros", "fecha_creacion", "TEXT DEFAULT CURRENT_TIMESTAMP")

    agregar_columna(cursor, "viajes", "cliente_id", "INTEGER")
    agregar_columna(cursor, "viajes", "pago_camionero", "REAL DEFAULT 0")
    agregar_columna(cursor, "viajes", "estado", "TEXT DEFAULT 'Solicitado'")
    agregar_columna(cursor, "viajes", "camionero_id", "INTEGER")
    agregar_columna(cursor, "viajes", "camionero_nombre", "TEXT")
    agregar_columna(cursor, "viajes", "vehiculo_id", "INTEGER")
    agregar_columna(cursor, "viajes", "fecha_creacion", "TEXT DEFAULT CURRENT_TIMESTAMP")
    agregar_columna(cursor, "viajes", "fecha_asignacion", "TEXT")
    agregar_columna(cursor, "viajes", "fecha_recogida", "TEXT")
    agregar_columna(cursor, "viajes", "fecha_entrega", "TEXT")
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