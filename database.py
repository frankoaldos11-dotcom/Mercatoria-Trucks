import sqlite3

from db_config import USE_POSTGRES

DATABASE_NAME = "mercatoria.db"


class CursorWrapper:
    """Traduce ? a %s automáticamente cuando se usa PostgreSQL."""
    def __init__(self, cursor, use_postgres=False):
        self._cursor = cursor
        self._use_postgres = use_postgres

    def execute(self, sql, params=None):
        if self._use_postgres:
            sql = sql.replace("?", "%s")
        if params is not None:
            return self._cursor.execute(sql, params)
        return self._cursor.execute(sql)

    def executemany(self, sql, params):
        if self._use_postgres:
            sql = sql.replace("?", "%s")
        return self._cursor.executemany(sql, params)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def lastrowid(self):
        if self._use_postgres:
            try:
                self._cursor.execute("SELECT lastval()")
                row = self._cursor.fetchone()
                if row:
                    return row[0] if not hasattr(row, 'keys') else row['lastval']
            except Exception:
                pass
        return self._cursor.lastrowid

    @property
    def description(self):
        return self._cursor.description

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def __iter__(self):
        return iter(self._cursor)


class ConexionWrapper:
    """Wrapper de conexión que devuelve CursorWrapper en lugar del cursor nativo."""
    def __init__(self, conn, use_postgres=False):
        self._conn = conn
        self._use_postgres = use_postgres

    def cursor(self):
        return CursorWrapper(self._conn.cursor(), self._use_postgres)

    def commit(self):
        return self._conn.commit()

    def close(self):
        return self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._conn.__exit__(*args)


def conectar():
    if USE_POSTGRES:
        from database_pg import conectar_pg
        conn = conectar_pg()
        return ConexionWrapper(conn, use_postgres=True)
    else:
        conexion = sqlite3.connect(DATABASE_NAME)
        conexion.row_factory = sqlite3.Row
        return ConexionWrapper(conexion, use_postgres=False)


def sql_mes_actual(columna: str = "fecha_creacion") -> str:
    """Devuelve un fragmento SQL que filtra por el mes actual, compatible con SQLite y PostgreSQL."""
    if USE_POSTGRES:
        return f"TO_CHAR({columna}, 'YYYY-MM') = TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM')"
    return f"strftime('%Y-%m', {columna}) = strftime('%Y-%m', 'now')"


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
        categoria TEXT DEFAULT 'Normal',
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
    CREATE TABLE IF NOT EXISTS rutas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        origen TEXT NOT NULL,
        destino TEXT NOT NULL,
        zona TEXT,
        km_oficiales REAL DEFAULT 0,
        tarifa_km REAL,
        activa INTEGER DEFAULT 1,
        fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS camionero_ruta (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        camionero_id INTEGER NOT NULL,
        ruta_id INTEGER NOT NULL,
        fecha_asignacion TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (camionero_id) REFERENCES camioneros(id),
        FOREIGN KEY (ruta_id) REFERENCES rutas(id),
        UNIQUE(camionero_id, ruta_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tipos_vehiculo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        descripcion TEXT,
        capacidad_ton REAL,
        activo INTEGER DEFAULT 1
    )
    """)
    for _tv in ["Plancha", "Rastra", "Furgón", "Camión cerrado",
                "Camión refrigerado", "Portacontenedor", "Camioneta", "Otro"]:
        cursor.execute(
            "INSERT OR IGNORE INTO tipos_vehiculo (nombre) VALUES (?)", (_tv,)
        )

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS catalogo_tipo_transporte (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        activo INTEGER DEFAULT 1
    )
    """)
    for _t in ["Rastra", "Plancha", "Furgón", "Camión cerrado",
               "Camión refrigerado", "Portacontenedor", "Camioneta", "Otro"]:
        cursor.execute(
            "INSERT OR IGNORE INTO catalogo_tipo_transporte (nombre) VALUES (?)", (_t,)
        )

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tarifas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ruta_id INTEGER NOT NULL,
        tipo_vehiculo_id INTEGER NOT NULL,
        precio_cliente REAL NOT NULL DEFAULT 0,
        pago_camionero REAL NOT NULL DEFAULT 0,
        precio_km_cliente REAL DEFAULT 0,
        precio_km_camionero REAL DEFAULT 0,
        combustible_estimado REAL DEFAULT 0,
        vigencia_desde TEXT,
        vigencia_hasta TEXT,
        activa INTEGER DEFAULT 1,
        fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (ruta_id) REFERENCES rutas(id),
        FOREIGN KEY (tipo_vehiculo_id) REFERENCES tipos_vehiculo(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cotizaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER,
        ruta_id INTEGER NOT NULL,
        tipo_vehiculo_id INTEGER NOT NULL,
        km REAL NOT NULL,
        precio_calculado REAL NOT NULL,
        precio_final REAL NOT NULL,
        pago_camionero REAL NOT NULL,
        combustible_estimado REAL DEFAULT 0,
        beneficio_estimado REAL DEFAULT 0,
        modificado_manualmente INTEGER DEFAULT 0,
        motivo_modificacion TEXT,
        usuario_modificacion INTEGER,
        estado TEXT DEFAULT 'borrador',
        fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (cliente_id) REFERENCES clientes(id),
        FOREIGN KEY (ruta_id) REFERENCES rutas(id),
        FOREIGN KEY (tipo_vehiculo_id) REFERENCES tipos_vehiculo(id),
        FOREIGN KEY (usuario_modificacion) REFERENCES usuarios(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS viajes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente TEXT,
        cliente_id INTEGER,
        ruta_id INTEGER,
        tarifa_id INTEGER,
        tipo_vehiculo_id INTEGER,
        origen TEXT,
        destino TEXT,
        precio REAL DEFAULT 0,
        precio_calculado REAL DEFAULT 0,
        precio_final REAL DEFAULT 0,
        precio_editado INTEGER DEFAULT 0,
        motivo_edicion_precio TEXT,
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
        observaciones TEXT,
        referencia_cliente TEXT,
        prioridad TEXT DEFAULT 'Normal',
        tipo_carga TEXT,
        tipo_transporte TEXT,
        cantidad_contenedores INTEGER,
        numero_contenedor TEXT,
        peso_toneladas REAL,
        observaciones_operativas TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS viaje_tramos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        viaje_id INTEGER NOT NULL,
        ruta_id INTEGER NOT NULL,
        orden INTEGER NOT NULL,
        estado TEXT DEFAULT 'pendiente',
        fecha_llegada TIMESTAMP,
        FOREIGN KEY (viaje_id) REFERENCES viajes(id),
        FOREIGN KEY (ruta_id) REFERENCES rutas(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS movimientos_viaje (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        viaje_id INTEGER,
        tipo TEXT,
        monto REAL DEFAULT 0,
        descripcion TEXT,
        fecha TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS configuracion (
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
    agregar_columna(cursor, "rutas", "km_oficiales", "REAL DEFAULT 0")
    agregar_columna(cursor, "rutas", "tarifa_km", "REAL")
    agregar_columna(cursor, "rutas", "activa", "INTEGER DEFAULT 1")
    agregar_columna(cursor, "viajes", "cliente_id", "INTEGER")
    agregar_columna(cursor, "viajes", "ruta_id", "INTEGER")
    agregar_columna(cursor, "viajes", "tarifa_id", "INTEGER")
    agregar_columna(cursor, "viajes", "tipo_vehiculo_id", "INTEGER")
    agregar_columna(cursor, "viajes", "precio_calculado", "REAL DEFAULT 0")
    agregar_columna(cursor, "viajes", "precio_final", "REAL DEFAULT 0")
    agregar_columna(cursor, "viajes", "precio_editado", "INTEGER DEFAULT 0")
    agregar_columna(cursor, "viajes", "motivo_edicion_precio", "TEXT")
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
    agregar_columna(cursor, "viajes", "referencia_cliente", "TEXT")
    agregar_columna(cursor, "viajes", "prioridad", "TEXT DEFAULT 'Normal'")
    agregar_columna(cursor, "viajes", "tipo_carga", "TEXT")
    agregar_columna(cursor, "viajes", "tipo_transporte", "TEXT")
    agregar_columna(cursor, "viajes", "cantidad_contenedores", "INTEGER")
    agregar_columna(cursor, "viajes", "numero_contenedor", "TEXT")
    agregar_columna(cursor, "viajes", "peso_toneladas", "REAL")
    agregar_columna(cursor, "viajes", "observaciones_operativas", "TEXT")
    agregar_columna(cursor, "viajes", "estado_pago_camionero",  "TEXT DEFAULT 'Pendiente'")
    agregar_columna(cursor, "viajes", "tipo_pago_camionero",    "TEXT")
    agregar_columna(cursor, "viajes", "observacion_pago",       "TEXT")
    agregar_columna(cursor, "viajes", "monto_pagado",           "REAL")
    agregar_columna(cursor, "viajes", "fecha_pago_camionero",   "TEXT")
    agregar_columna(cursor, "clientes", "documento_identidad", "TEXT")
    agregar_columna(cursor, "clientes", "deleted_at",  "TIMESTAMP")
    agregar_columna(cursor, "clientes", "deleted_by",  "TEXT")
    agregar_columna(cursor, "camioneros", "carnet_identidad",   "TEXT")
    agregar_columna(cursor, "camioneros", "licencia_operativa", "TEXT")
    agregar_columna(cursor, "camioneros", "empresa",            "TEXT")
    agregar_columna(cursor, "camioneros", "deleted_at",         "TIMESTAMP")
    agregar_columna(cursor, "camioneros", "deleted_by",         "TEXT")
    agregar_columna(cursor, "vehiculos",  "chapa_remolque",     "TEXT")
    agregar_columna(cursor, "viajes",     "cotizacion_id",      "INTEGER")
    agregar_columna(cursor, "viajes",     "km",                 "REAL")
    agregar_columna(cursor, "viajes",     "kilometros",         "REAL")
    agregar_columna(cursor, "viajes",     "precio_cliente",     "REAL")
    agregar_columna(cursor, "viajes",     "combustible_estimado","REAL")
    agregar_columna(cursor, "viajes",     "beneficio_estimado", "REAL")
    agregar_columna(cursor, "viajes",     "vehiculo_placa",     "TEXT")
    agregar_columna(cursor, "viajes",     "deleted_at",         "TIMESTAMP")
    agregar_columna(cursor, "viajes",     "deleted_by",         "TEXT")
    agregar_columna(cursor, "viajes",     "forma_cobro",        "TEXT")
    agregar_columna(cursor, "viajes",     "codigo_transaccion", "TEXT")
    agregar_columna(cursor, "viajes",     "comentario_cobro",   "TEXT")
    agregar_columna(cursor, "viajes",     "fecha_cobro",        "TEXT")
    agregar_columna(cursor, "viajes",     "monto_cobrado",      "REAL")
    agregar_columna(cursor, "viajes",     "verificado_financiero", "INTEGER DEFAULT 0")
    agregar_columna(cursor, "viajes",     "verificado_por",        "TEXT")
    agregar_columna(cursor, "viajes",     "fecha_verificacion",    "TEXT")
    agregar_columna(cursor, "viajes",     "reabierto_en",          "TIMESTAMP")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS configuracion_texto (
        clave TEXT PRIMARY KEY,
        valor TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reset_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT UNIQUE,
        usuario TEXT,
        expira TEXT,
        usado INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auditoria (
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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notas_viaje (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        viaje_id INTEGER NOT NULL,
        usuario TEXT NOT NULL,
        texto TEXT NOT NULL,
        fecha TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (viaje_id) REFERENCES viajes(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS viaje_checklist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        viaje_id INTEGER NOT NULL,
        item TEXT NOT NULL,
        completado INTEGER DEFAULT 0,
        completado_por TEXT,
        fecha_completado TEXT,
        FOREIGN KEY (viaje_id) REFERENCES viajes(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS incidencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        viaje_id INTEGER NOT NULL,
        categoria TEXT NOT NULL,
        descripcion TEXT,
        usuario TEXT,
        fecha_hora TEXT DEFAULT CURRENT_TIMESTAMP,
        estado TEXT DEFAULT 'Abierta',
        FOREIGN KEY (viaje_id) REFERENCES viajes(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historial_viaje (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        viaje_id INTEGER NOT NULL,
        usuario TEXT NOT NULL,
        accion TEXT NOT NULL,
        detalle TEXT,
        fecha_hora TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (viaje_id) REFERENCES viajes(id)
    )
    """)

    cursor.execute("SELECT id FROM usuarios WHERE usuario = ?", ("admin",))
    if not cursor.fetchone():
        hash_admin = bcrypt.generate_password_hash("1234").decode("utf-8")
        cursor.execute("""
        INSERT INTO usuarios (usuario, password, rol)
        VALUES (?, ?, ?)
        """, ("admin", hash_admin, "admin"))

    _indices = [
        ("idx_viajes_estado",         "viajes",     "estado"),
        ("idx_viajes_cliente_id",      "viajes",     "cliente_id"),
        ("idx_viajes_camionero_id",    "viajes",     "camionero_id"),
        ("idx_viajes_fecha_creacion",  "viajes",     "fecha_creacion"),
        ("idx_clientes_activo",        "clientes",   "activo"),
        ("idx_camioneros_estado",      "camioneros", "estado"),
        ("idx_auditoria_fecha",        "auditoria",  "fecha"),
        ("idx_viaje_tramos_viaje_id",   "viaje_tramos", "viaje_id"),
    ]
    for _nombre, _tabla, _col in _indices:
        cursor.execute(
            f"CREATE INDEX IF NOT EXISTS {_nombre} ON {_tabla}({_col})"
        )

    conexion.commit()
    conexion.close()


INCIDENCIAS_CATEGORIAS = ["Retraso", "Avería", "Puerto", "Cliente", "Combustible", "Documentación", "Pago", "Cobro", "Otro"]
INCIDENCIAS_ESTADOS = ["Abierta", "En seguimiento", "Resuelta"]

CHECKLIST_ITEMS_DEFAULT = [
    "Solicitud revisada",
    "Km calculados",
    "Combustible calculado",
    "Pago camionero calculado",
    "Camionero asignado",
    "Vehículo confirmado",
    "Documentación enviada",
    "Combustible confirmado",
    "Contenedor extraído / carga recogida",
    "Descarga realizada",
    "Pago camionero confirmado",
    "Cobro cliente confirmado",
    "Documentos archivados",
]


def crear_checklist_viaje(cursor, viaje_id):
    """Inserta los ítems del checklist operativo para un viaje recién creado."""
    for item in CHECKLIST_ITEMS_DEFAULT:
        cursor.execute(
            "INSERT INTO viaje_checklist (viaje_id, item) VALUES (?, ?)",
            (viaje_id, item)
        )
