import sqlite3


DATABASE_NAME = "mercatoria.db"


def conectar():
    conexion = sqlite3.connect(DATABASE_NAME)
    conexion.row_factory = sqlite3.Row
    return conexion


def tabla_existe(cursor, tabla):
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name = ?
    """, (tabla,))
    return cursor.fetchone() is not None


def columna_existe(cursor, tabla, columna):
    cursor.execute(f"PRAGMA table_info({tabla})")
    columnas = cursor.fetchall()
    return any(col["name"] == columna for col in columnas)


def agregar_columna(cursor, tabla, columna, definicion):
    if tabla_existe(cursor, tabla) and not columna_existe(cursor, tabla, columna):
        cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}")


def ejecutar_migraciones():
    conexion = conectar()
    cursor = conexion.cursor()

    agregar_columna(cursor, "viajes", "cotizacion_id", "INTEGER")
    agregar_columna(cursor, "viajes", "cliente", "TEXT")
    agregar_columna(cursor, "viajes", "cliente_id", "INTEGER")
    agregar_columna(cursor, "viajes", "ruta_id", "INTEGER")
    agregar_columna(cursor, "viajes", "tarifa_id", "INTEGER")
    agregar_columna(cursor, "viajes", "tipo_vehiculo_id", "INTEGER")
    agregar_columna(cursor, "viajes", "origen", "TEXT")
    agregar_columna(cursor, "viajes", "destino", "TEXT")
    agregar_columna(cursor, "viajes", "km", "REAL")
    agregar_columna(cursor, "viajes", "kilometros", "REAL")
    agregar_columna(cursor, "viajes", "precio", "REAL")
    agregar_columna(cursor, "viajes", "precio_cliente", "REAL")
    agregar_columna(cursor, "viajes", "precio_calculado", "REAL")
    agregar_columna(cursor, "viajes", "precio_final", "REAL")
    agregar_columna(cursor, "viajes", "combustible", "REAL")
    agregar_columna(cursor, "viajes", "combustible_estimado", "REAL")
    agregar_columna(cursor, "viajes", "pago_camionero", "REAL")
    agregar_columna(cursor, "viajes", "beneficio", "REAL")
    agregar_columna(cursor, "viajes", "beneficio_estimado", "REAL")
    agregar_columna(cursor, "viajes", "camionero_id", "INTEGER")
    agregar_columna(cursor, "viajes", "camionero_nombre", "TEXT")
    agregar_columna(cursor, "viajes", "vehiculo_id", "INTEGER")
    agregar_columna(cursor, "viajes", "vehiculo_placa", "TEXT")
    agregar_columna(cursor, "viajes", "estado", "TEXT DEFAULT 'Pendiente'")
    agregar_columna(cursor, "viajes", "observaciones", "TEXT")
    agregar_columna(cursor, "viajes", "referencia_cliente",      "TEXT")
    agregar_columna(cursor, "viajes", "prioridad",               "TEXT DEFAULT 'Normal'")
    agregar_columna(cursor, "viajes", "tipo_carga",              "TEXT")
    agregar_columna(cursor, "viajes", "tipo_transporte",         "TEXT")
    agregar_columna(cursor, "viajes", "cantidad_contenedores",   "INTEGER")
    agregar_columna(cursor, "viajes", "numero_contenedor",       "TEXT")
    agregar_columna(cursor, "viajes", "peso_toneladas",          "REAL")
    agregar_columna(cursor, "viajes", "observaciones_operativas","TEXT")
    agregar_columna(cursor, "viajes", "precio_editado",          "INTEGER DEFAULT 0")
    agregar_columna(cursor, "viajes", "motivo_edicion_precio",   "TEXT")

    agregar_columna(cursor, "vehiculos", "tipo_vehiculo_id", "INTEGER")
    agregar_columna(cursor, "vehiculos", "matricula", "TEXT")
    agregar_columna(cursor, "vehiculos", "placa", "TEXT")
    agregar_columna(cursor, "vehiculos", "marca", "TEXT")
    agregar_columna(cursor, "vehiculos", "modelo", "TEXT")
    agregar_columna(cursor, "vehiculos", "tipo", "TEXT")
    agregar_columna(cursor, "vehiculos", "capacidad", "TEXT")
    agregar_columna(cursor, "vehiculos", "combustible", "TEXT")
    agregar_columna(cursor, "vehiculos", "estado", "TEXT DEFAULT 'Disponible'")
    agregar_columna(cursor, "vehiculos", "activo", "INTEGER DEFAULT 1")

    agregar_columna(cursor, "cotizaciones", "cliente_id", "INTEGER")
    agregar_columna(cursor, "cotizaciones", "ruta_id", "INTEGER")
    agregar_columna(cursor, "cotizaciones", "tipo_vehiculo_id", "INTEGER")
    agregar_columna(cursor, "cotizaciones", "km", "REAL")
    agregar_columna(cursor, "cotizaciones", "precio_calculado", "REAL")
    agregar_columna(cursor, "cotizaciones", "precio_final", "REAL")
    agregar_columna(cursor, "cotizaciones", "pago_camionero", "REAL")
    agregar_columna(cursor, "cotizaciones", "combustible_estimado", "REAL")
    agregar_columna(cursor, "cotizaciones", "beneficio_estimado", "REAL")
    agregar_columna(cursor, "cotizaciones", "modificado_manualmente", "INTEGER DEFAULT 0")
    agregar_columna(cursor, "cotizaciones", "motivo_modificacion", "TEXT")
    agregar_columna(cursor, "cotizaciones", "usuario_modificacion", "INTEGER")
    agregar_columna(cursor, "cotizaciones", "estado", "TEXT DEFAULT 'borrador'")

    # Tabla configuracion (parámetros financieros)
    if not tabla_existe(cursor, "configuracion"):
        cursor.execute("""
        CREATE TABLE configuracion (
            clave TEXT PRIMARY KEY,
            valor REAL NOT NULL,
            descripcion TEXT
        )
        """)

    defaults = [
        ("tarifa_km",                    1.5,  "Tarifa por km cobrada al camionero (USD/km)"),
        ("margen_combustible_divisor",   2.0,  "Divisor para calcular combustible: pago_camionero / divisor"),
        ("multiplicador_pago_camionero", 2.5,  "Multiplicador para estimar precio cliente desde pago camionero"),
        ("minimo_km_garantizado",      120.0,  "Km mínimo garantizado para liquidación"),
        ("minimo_pago_usd",            150.0,  "Pago mínimo garantizado al camionero en USD"),
        ("comision_mercatoria_porcentaje", 20.0, "Porcentaje de comisión de Mercatoria sobre precio cliente"),
    ]
    for clave, valor, desc in defaults:
        cursor.execute(
            "INSERT OR IGNORE INTO configuracion (clave, valor, descripcion) VALUES (?, ?, ?)",
            (clave, valor, desc)
        )

    agregar_columna(cursor, "rutas", "tarifa_km", "REAL")

    # Sprint 10: portal cliente — datos de perfil en tabla usuarios
    agregar_columna(cursor, "usuarios", "nombre", "TEXT")
    agregar_columna(cursor, "usuarios", "apellidos", "TEXT")
    agregar_columna(cursor, "usuarios", "telefono", "TEXT")
    agregar_columna(cursor, "usuarios", "empresa", "TEXT")

    if not tabla_existe(cursor, "camionero_ruta"):
        cursor.execute("""
        CREATE TABLE camionero_ruta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            camionero_id INTEGER NOT NULL,
            ruta_id INTEGER NOT NULL,
            fecha_asignacion TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (camionero_id) REFERENCES camioneros(id),
            FOREIGN KEY (ruta_id) REFERENCES rutas(id),
            UNIQUE(camionero_id, ruta_id)
        )
        """)

    if not tabla_existe(cursor, "configuracion_texto"):
        cursor.execute("""
        CREATE TABLE configuracion_texto (
            clave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        )
        """)

    if not tabla_existe(cursor, "reset_tokens"):
        cursor.execute("""
        CREATE TABLE reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE,
            usuario TEXT,
            expira TEXT,
            usado INTEGER DEFAULT 0
        )
        """)

    if not tabla_existe(cursor, "auditoria"):
        cursor.execute("""
        CREATE TABLE auditoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT DEFAULT CURRENT_TIMESTAMP,
            usuario TEXT,
            rol TEXT,
            accion TEXT,
            categoria TEXT,
            entidad TEXT,
            entidad_id INTEGER,
            detalle TEXT
        )
        """)

    conexion.commit()
    conexion.close()