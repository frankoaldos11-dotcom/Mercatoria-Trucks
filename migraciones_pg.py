import os
import psycopg2
import psycopg2.extras


def _conectar():
    url = os.environ.get("DATABASE_URL")
    conn = psycopg2.connect(url)
    return conn


def ejecutar_migraciones_pg():
    from extensions import bcrypt

    conn = _conectar()
    cur = conn.cursor()

    import os
    if os.environ.get("SKIP_MIGRATIONS") == "true":
        print("[migraciones_pg] SKIP_MIGRATIONS=true — omitiendo migraciones.")
        conn.close()
        return

    # Verificación ligera: si la tabla principal ya existe, saltar
    cur.execute("""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'usuarios'
    """)
    if cur.fetchone()[0] > 0:
        # Schema ya existe — asegurar admin y columnas nuevas
        try:
            cur.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS categoria TEXT DEFAULT 'Normal'")
            conn.commit()
        except Exception:
            conn.rollback()

        try:
            cur.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS documento_identidad TEXT")
            conn.commit()
        except Exception:
            conn.rollback()

        nuevas_columnas_viajes = [
            ("referencia_cliente",      "TEXT"),
            ("prioridad",               "TEXT DEFAULT 'Normal'"),
            ("tipo_carga",              "TEXT"),
            ("tipo_transporte",         "TEXT"),
            ("cantidad_contenedores",   "INTEGER"),
            ("numero_contenedor",       "TEXT"),
            ("peso_toneladas",          "REAL"),
            ("observaciones_operativas","TEXT"),
            ("estado_pago_camionero",   "TEXT DEFAULT 'Pendiente'"),
            ("tipo_pago_camionero",     "TEXT"),
            ("observacion_pago",        "TEXT"),
            ("monto_pagado",            "REAL"),
            ("fecha_pago_camionero",    "TEXT"),
            ("verificado_financiero",   "INTEGER DEFAULT 0"),
            ("verificado_por",          "TEXT"),
            ("fecha_verificacion",      "TEXT"),
        ]
        for col, defn in nuevas_columnas_viajes:
            try:
                cur.execute(f"ALTER TABLE viajes ADD COLUMN IF NOT EXISTS {col} {defn}")
                conn.commit()
            except Exception:
                conn.rollback()

        try:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS viaje_checklist (
                id SERIAL PRIMARY KEY,
                viaje_id INTEGER NOT NULL,
                item TEXT NOT NULL,
                completado INTEGER DEFAULT 0,
                completado_por TEXT,
                fecha_completado TIMESTAMP
            )
            """)
            conn.commit()
        except Exception:
            conn.rollback()

        try:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS incidencias (
                id SERIAL PRIMARY KEY,
                viaje_id INTEGER NOT NULL,
                categoria TEXT NOT NULL,
                descripcion TEXT,
                usuario TEXT,
                fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                estado TEXT DEFAULT 'Abierta'
            )
            """)
            conn.commit()
        except Exception:
            conn.rollback()

        try:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS catalogo_tipo_transporte (
                id SERIAL PRIMARY KEY,
                nombre TEXT NOT NULL UNIQUE,
                activo INTEGER DEFAULT 1
            )
            """)
            conn.commit()
            for _t in ["Rastra", "Plancha", "Furgón", "Camión cerrado",
                       "Camión refrigerado", "Portacontenedor", "Camioneta", "Otro"]:
                cur.execute(
                    "INSERT INTO catalogo_tipo_transporte (nombre) VALUES (%s) ON CONFLICT (nombre) DO NOTHING",
                    (_t,)
                )
            conn.commit()
        except Exception:
            conn.rollback()

        try:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS viaje_tramos (
                id SERIAL PRIMARY KEY,
                viaje_id INTEGER NOT NULL,
                ruta_id INTEGER NOT NULL,
                orden INTEGER NOT NULL,
                estado TEXT DEFAULT 'pendiente',
                fecha_llegada TIMESTAMP,
                FOREIGN KEY (viaje_id) REFERENCES viajes(id),
                FOREIGN KEY (ruta_id) REFERENCES rutas(id)
            )
            """)
            conn.commit()
        except Exception:
            conn.rollback()

        _indices = [
            ("idx_viajes_estado",         "viajes",     "estado"),
            ("idx_viajes_cliente_id",      "viajes",     "cliente_id"),
            ("idx_viajes_camionero_id",    "viajes",     "camionero_id"),
            ("idx_viajes_fecha_creacion",  "viajes",     "fecha_creacion"),
            ("idx_clientes_activo",        "clientes",   "activo"),
            ("idx_camioneros_estado",      "camioneros", "estado"),
            ("idx_auditoria_fecha",        "auditoria",  "fecha"),
            ("idx_viaje_tramos_viaje_id",  "viaje_tramos", "viaje_id"),
        ]
        for _nombre, _tabla, _col in _indices:
            try:
                cur.execute(
                    f"CREATE INDEX IF NOT EXISTS {_nombre} ON {_tabla}({_col})"
                )
                conn.commit()
            except Exception:
                conn.rollback()

        cur.execute("SELECT id FROM usuarios WHERE usuario = 'admin'")
        if not cur.fetchone():
            from flask_bcrypt import Bcrypt
            _bcrypt = Bcrypt()
            hash_pw = _bcrypt.generate_password_hash("admin1234").decode("utf-8")
            cur.execute(
                "INSERT INTO usuarios (usuario, password, rol) VALUES (%s, %s, %s)",
                ("admin", hash_pw, "admin")
            )
            conn.commit()
        conn.close()
        print("[migraciones_pg] Schema existente detectado — migraciones incrementales aplicadas.")
        return

    print("[migraciones_pg] Schema nuevo — ejecutando migraciones completas.")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        usuario TEXT UNIQUE,
        password TEXT,
        rol TEXT,
        nombre TEXT,
        apellidos TEXT,
        telefono TEXT,
        empresa TEXT,
        activo INTEGER DEFAULT 1,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id SERIAL PRIMARY KEY,
        usuario_id INTEGER,
        nombre TEXT,
        empresa TEXT,
        contacto TEXT,
        telefono TEXT,
        email TEXT,
        direccion TEXT,
        activo INTEGER DEFAULT 1,
        categoria TEXT DEFAULT 'Normal',
        documento_identidad TEXT,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS camioneros (
        id SERIAL PRIMARY KEY,
        nombre TEXT,
        telefono TEXT,
        licencia TEXT,
        matricula TEXT,
        tipo TEXT,
        capacidad TEXT,
        estado TEXT DEFAULT 'Disponible',
        activo INTEGER DEFAULT 1,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS vehiculos (
        id SERIAL PRIMARY KEY,
        camionero_id INTEGER,
        tipo_vehiculo_id INTEGER,
        matricula TEXT,
        placa TEXT,
        marca TEXT,
        modelo TEXT,
        tipo TEXT,
        capacidad TEXT,
        combustible TEXT,
        estado TEXT DEFAULT 'Disponible',
        activo INTEGER DEFAULT 1,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS rutas (
        id SERIAL PRIMARY KEY,
        nombre TEXT,
        origen TEXT NOT NULL,
        destino TEXT NOT NULL,
        zona TEXT,
        km_oficiales REAL DEFAULT 0,
        tarifa_km REAL,
        activa INTEGER DEFAULT 1,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS camionero_ruta (
        id SERIAL PRIMARY KEY,
        camionero_id INTEGER NOT NULL,
        ruta_id INTEGER NOT NULL,
        fecha_asignacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (camionero_id) REFERENCES camioneros(id),
        FOREIGN KEY (ruta_id) REFERENCES rutas(id),
        UNIQUE(camionero_id, ruta_id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tipos_vehiculo (
        id SERIAL PRIMARY KEY,
        nombre TEXT NOT NULL UNIQUE,
        descripcion TEXT,
        capacidad_ton REAL,
        activo INTEGER DEFAULT 1
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS catalogo_tipo_transporte (
        id SERIAL PRIMARY KEY,
        nombre TEXT NOT NULL UNIQUE,
        activo INTEGER DEFAULT 1
    )
    """)
    for _t in ["Rastra", "Plancha", "Furgón", "Camión cerrado",
               "Camión refrigerado", "Portacontenedor", "Camioneta", "Otro"]:
        cur.execute(
            "INSERT INTO catalogo_tipo_transporte (nombre) VALUES (%s) ON CONFLICT (nombre) DO NOTHING",
            (_t,)
        )

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tarifas (
        id SERIAL PRIMARY KEY,
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
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (ruta_id) REFERENCES rutas(id),
        FOREIGN KEY (tipo_vehiculo_id) REFERENCES tipos_vehiculo(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS cotizaciones (
        id SERIAL PRIMARY KEY,
        cliente_id INTEGER,
        ruta_id INTEGER NOT NULL,
        tipo_vehiculo_id INTEGER NOT NULL,
        km REAL NOT NULL DEFAULT 0,
        precio_calculado REAL NOT NULL DEFAULT 0,
        precio_final REAL NOT NULL DEFAULT 0,
        pago_camionero REAL NOT NULL DEFAULT 0,
        combustible_estimado REAL DEFAULT 0,
        beneficio_estimado REAL DEFAULT 0,
        modificado_manualmente INTEGER DEFAULT 0,
        motivo_modificacion TEXT,
        usuario_modificacion INTEGER,
        estado TEXT DEFAULT 'borrador',
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (cliente_id) REFERENCES clientes(id),
        FOREIGN KEY (ruta_id) REFERENCES rutas(id),
        FOREIGN KEY (tipo_vehiculo_id) REFERENCES tipos_vehiculo(id),
        FOREIGN KEY (usuario_modificacion) REFERENCES usuarios(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS viajes (
        id SERIAL PRIMARY KEY,
        cliente TEXT,
        cliente_id INTEGER,
        cotizacion_id INTEGER,
        ruta_id INTEGER,
        tarifa_id INTEGER,
        tipo_vehiculo_id INTEGER,
        origen TEXT,
        destino TEXT,
        km REAL DEFAULT 0,
        kilometros REAL DEFAULT 0,
        precio REAL DEFAULT 0,
        precio_cliente REAL DEFAULT 0,
        precio_calculado REAL DEFAULT 0,
        precio_final REAL DEFAULT 0,
        precio_editado INTEGER DEFAULT 0,
        motivo_edicion_precio TEXT,
        combustible REAL DEFAULT 0,
        combustible_estimado REAL DEFAULT 0,
        pago_camionero REAL DEFAULT 0,
        camionero REAL DEFAULT 0,
        comision REAL DEFAULT 0,
        beneficio REAL DEFAULT 0,
        beneficio_estimado REAL DEFAULT 0,
        estado TEXT DEFAULT 'Solicitado',
        camionero_id INTEGER,
        camionero_nombre TEXT,
        vehiculo_id INTEGER,
        vehiculo_placa TEXT,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
        observaciones_operativas TEXT,
        estado_pago_camionero TEXT DEFAULT 'Pendiente',
        tipo_pago_camionero TEXT,
        observacion_pago TEXT,
        monto_pagado REAL,
        fecha_pago_camionero TEXT,
        verificado_financiero INTEGER DEFAULT 0,
        verificado_por TEXT,
        fecha_verificacion TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS movimientos_viaje (
        id SERIAL PRIMARY KEY,
        viaje_id INTEGER,
        tipo TEXT,
        monto REAL DEFAULT 0,
        descripcion TEXT,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS configuracion (
        clave TEXT PRIMARY KEY,
        valor REAL NOT NULL,
        descripcion TEXT
    )
    """)

    defaults = [
        ("tarifa_km",                      1.5,  "Tarifa por km cobrada al camionero (USD/km)"),
        ("margen_combustible_divisor",     2.0,  "Divisor para calcular combustible: pago_camionero / divisor"),
        ("multiplicador_pago_camionero",   2.5,  "Multiplicador para estimar precio cliente desde pago camionero"),
        ("minimo_km_garantizado",        120.0,  "Km mínimo garantizado para liquidación"),
        ("minimo_pago_usd",              150.0,  "Pago mínimo garantizado al camionero en USD"),
        ("comision_mercatoria_porcentaje", 20.0, "Porcentaje de comisión de Mercatoria sobre precio cliente"),
    ]
    for clave, valor, desc in defaults:
        cur.execute(
            "INSERT INTO configuracion (clave, valor, descripcion) VALUES (%s, %s, %s) ON CONFLICT (clave) DO NOTHING",
            (clave, valor, desc)
        )

    cur.execute("""
    CREATE TABLE IF NOT EXISTS configuracion_texto (
        clave TEXT PRIMARY KEY,
        valor TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS reset_tokens (
        id SERIAL PRIMARY KEY,
        token TEXT UNIQUE,
        usuario TEXT,
        expira TEXT,
        usado INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS auditoria (
        id SERIAL PRIMARY KEY,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        usuario TEXT,
        rol TEXT,
        accion TEXT,
        categoria TEXT,
        entidad TEXT,
        entidad_id INTEGER,
        detalle TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notas_viaje (
        id SERIAL PRIMARY KEY,
        viaje_id INTEGER NOT NULL,
        usuario TEXT NOT NULL,
        texto TEXT NOT NULL,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (viaje_id) REFERENCES viajes(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS viaje_checklist (
        id SERIAL PRIMARY KEY,
        viaje_id INTEGER NOT NULL,
        item TEXT NOT NULL,
        completado INTEGER DEFAULT 0,
        completado_por TEXT,
        fecha_completado TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS incidencias (
        id SERIAL PRIMARY KEY,
        viaje_id INTEGER NOT NULL,
        categoria TEXT NOT NULL,
        descripcion TEXT,
        usuario TEXT,
        fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        estado TEXT DEFAULT 'Abierta',
        FOREIGN KEY (viaje_id) REFERENCES viajes(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS viaje_tramos (
        id SERIAL PRIMARY KEY,
        viaje_id INTEGER NOT NULL,
        ruta_id INTEGER NOT NULL,
        orden INTEGER NOT NULL,
        estado TEXT DEFAULT 'pendiente',
        fecha_llegada TIMESTAMP,
        FOREIGN KEY (viaje_id) REFERENCES viajes(id),
        FOREIGN KEY (ruta_id) REFERENCES rutas(id)
    )
    """)

    _indices = [
        ("idx_viajes_estado",         "viajes",     "estado"),
        ("idx_viajes_cliente_id",      "viajes",     "cliente_id"),
        ("idx_viajes_camionero_id",    "viajes",     "camionero_id"),
        ("idx_viajes_fecha_creacion",  "viajes",     "fecha_creacion"),
        ("idx_clientes_activo",        "clientes",   "activo"),
        ("idx_camioneros_estado",      "camioneros", "estado"),
        ("idx_auditoria_fecha",        "auditoria",  "fecha"),
        ("idx_viaje_tramos_viaje_id",  "viaje_tramos", "viaje_id"),
    ]
    for _nombre, _tabla, _col in _indices:
        cur.execute(f"CREATE INDEX IF NOT EXISTS {_nombre} ON {_tabla}({_col})")

    cur.execute("SELECT id FROM usuarios WHERE usuario = %s", ("admin",))
    if not cur.fetchone():
        hash_admin = bcrypt.generate_password_hash("1234").decode("utf-8")
        cur.execute(
            "INSERT INTO usuarios (usuario, password, rol) VALUES (%s, %s, %s)",
            ("admin", hash_admin, "admin")
        )

    conn.commit()
    cur.close()
    conn.close()
