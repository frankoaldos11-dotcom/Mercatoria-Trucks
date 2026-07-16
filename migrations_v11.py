"""
Migración v1.1 para PostgreSQL (producción).

Uso desde app.py (automático al arrancar):
    from migrations_v11 import aplicar_migraciones_v11
    aplicar_migraciones_v11()

Uso manual desde Render Shell (una sola vez):
    python migrations_v11.py

No depende de SKIP_MIGRATIONS. Idempotente: safe de re-ejecutar.
"""

import os
import sys
import psycopg2
import psycopg2.extras


def run(conn, cur, sql, desc=""):
    try:
        cur.execute(sql)
        conn.commit()
        label = desc or sql.strip()[:72]
        print(f"  OK  {label}")
    except Exception as e:
        conn.rollback()
        print(f"  --  {desc or ''}: {e}")


def run_many(conn, cur, statements):
    for sql, desc in statements:
        run(conn, cur, sql, desc)


def aplicar_migraciones_v11():
    """
    Función importable: se llama desde app.py al arrancar.
    No hace sys.exit — si DATABASE_URL falta simplemente avisa y retorna.
    """
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("[migrations_v11] DATABASE_URL no configurada — omitiendo.")
        return
    try:
        conn = psycopg2.connect(database_url)
    except Exception as e:
        print(f"[migrations_v11] No se pudo conectar a la BD: {e}")
        return
    _ejecutar(conn)


def main():
    """Punto de entrada para ejecución manual desde el shell."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("ERROR: La variable DATABASE_URL no está configurada.")
    conn = psycopg2.connect(database_url)
    _ejecutar(conn)


def _ejecutar(conn):
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    print("\n=== migrations_v11.py — Mercatoria Truck ===\n")

    # ── 1. usuarios — columnas nuevas ─────────────────────────────────────────
    print("[ usuarios ]")
    run_many(conn, cur, [
        ("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS nombre TEXT",             "nombre"),
        ("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS apellidos TEXT",          "apellidos"),
        ("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS telefono TEXT",           "telefono"),
        ("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS empresa TEXT",            "empresa"),
        ("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS activo INTEGER DEFAULT 1","activo"),
        ("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "fecha_creacion"),
    ])

    # ── 2. clientes — columnas nuevas ─────────────────────────────────────────
    print("\n[ clientes ]")
    run_many(conn, cur, [
        ("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS usuario_id INTEGER",      "usuario_id"),
        ("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS empresa TEXT",            "empresa"),
        ("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS contacto TEXT",           "contacto"),
        ("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS telefono TEXT",           "telefono"),
        ("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS email TEXT",              "email"),
        ("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS direccion TEXT",          "direccion"),
        ("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS activo INTEGER DEFAULT 1","activo"),
        ("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS categoria TEXT DEFAULT 'Normal'", "categoria"),
        ("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "fecha_creacion"),
    ])

    # ── 3. camioneros — columnas nuevas ───────────────────────────────────────
    print("\n[ camioneros ]")
    run_many(conn, cur, [
        ("ALTER TABLE camioneros ADD COLUMN IF NOT EXISTS licencia TEXT",         "licencia"),
        ("ALTER TABLE camioneros ADD COLUMN IF NOT EXISTS activo INTEGER DEFAULT 1", "activo"),
        ("ALTER TABLE camioneros ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "fecha_creacion"),
    ])

    # ── 4. rutas — columnas nuevas ────────────────────────────────────────────
    print("\n[ rutas ]")
    run_many(conn, cur, [
        ("ALTER TABLE rutas ADD COLUMN IF NOT EXISTS zona TEXT",                  "zona"),
        ("ALTER TABLE rutas ADD COLUMN IF NOT EXISTS km_oficiales REAL DEFAULT 0","km_oficiales"),
        ("ALTER TABLE rutas ADD COLUMN IF NOT EXISTS tarifa_km REAL",             "tarifa_km"),
        ("ALTER TABLE rutas ADD COLUMN IF NOT EXISTS activa INTEGER DEFAULT 1",   "activa"),
        ("ALTER TABLE rutas ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "fecha_creacion"),
    ])

    # ── 5. vehiculos — tabla nueva o columnas faltantes ───────────────────────
    print("\n[ vehiculos ]")
    run(conn, cur, """
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
    """, "CREATE TABLE IF NOT EXISTS vehiculos")
    # Por si la tabla ya existía con schema antiguo:
    run_many(conn, cur, [
        ("ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS camionero_id INTEGER",   "camionero_id"),
        ("ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS tipo_vehiculo_id INTEGER","tipo_vehiculo_id"),
        ("ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS matricula TEXT",         "matricula"),
        ("ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS placa TEXT",             "placa"),
        ("ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS marca TEXT",             "marca"),
        ("ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS modelo TEXT",            "modelo"),
        ("ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS tipo TEXT",              "tipo"),
        ("ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS capacidad TEXT",         "capacidad"),
        ("ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS combustible TEXT",       "combustible"),
        ("ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS estado TEXT DEFAULT 'Disponible'", "estado"),
        ("ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS activo INTEGER DEFAULT 1","activo"),
        ("ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "fecha_creacion"),
    ])

    # ── 6. viajes — columnas nuevas (todas las del sprint v1.1) ──────────────
    print("\n[ viajes ]")
    viajes_cols = [
        ("cotizacion_id",          "INTEGER"),
        ("ruta_id",                "INTEGER"),
        ("tarifa_id",              "INTEGER"),
        ("tipo_vehiculo_id",       "INTEGER"),
        ("km",                     "REAL DEFAULT 0"),
        ("kilometros",             "REAL DEFAULT 0"),
        ("precio_cliente",         "REAL DEFAULT 0"),
        ("precio_calculado",       "REAL DEFAULT 0"),
        ("precio_final",           "REAL DEFAULT 0"),
        ("precio_editado",         "INTEGER DEFAULT 0"),
        ("motivo_edicion_precio",  "TEXT"),
        ("combustible_estimado",   "REAL DEFAULT 0"),
        ("beneficio_estimado",     "REAL DEFAULT 0"),
        ("camionero_id",           "INTEGER"),
        ("camionero_nombre",       "TEXT"),
        ("vehiculo_id",            "INTEGER"),
        ("vehiculo_placa",         "TEXT"),
        ("fecha_asignacion",       "TEXT"),
        ("fecha_recogida",         "TEXT"),
        ("fecha_entrega",          "TEXT"),
        ("observaciones",          "TEXT"),
        ("referencia_cliente",     "TEXT"),
        ("prioridad",              "TEXT DEFAULT 'Normal'"),
        ("tipo_carga",             "TEXT"),
        ("tipo_transporte",        "TEXT"),
        ("cantidad_contenedores",  "INTEGER"),
        ("numero_contenedor",      "TEXT"),
        ("peso_toneladas",         "REAL"),
        ("observaciones_operativas","TEXT"),
        ("estado_pago_camionero",  "TEXT DEFAULT 'Pendiente'"),
        ("tipo_pago_camionero",    "TEXT"),
        ("observacion_pago",       "TEXT"),
        ("monto_pagado",           "REAL"),
        ("fecha_pago_camionero",   "TEXT"),
    ]
    for col, defn in viajes_cols:
        run(conn, cur,
            f"ALTER TABLE viajes ADD COLUMN IF NOT EXISTS {col} {defn}",
            col)

    # ── 7. Tablas nuevas ──────────────────────────────────────────────────────
    print("\n[ tipos_vehiculo ]")
    run(conn, cur, """
        CREATE TABLE IF NOT EXISTS tipos_vehiculo (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL UNIQUE,
            descripcion TEXT,
            capacidad_ton REAL,
            activo INTEGER DEFAULT 1
        )
    """, "CREATE TABLE IF NOT EXISTS tipos_vehiculo")

    print("\n[ camionero_ruta ]")
    run(conn, cur, """
        CREATE TABLE IF NOT EXISTS camionero_ruta (
            id SERIAL PRIMARY KEY,
            camionero_id INTEGER NOT NULL,
            ruta_id INTEGER NOT NULL,
            fecha_asignacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(camionero_id, ruta_id)
        )
    """, "CREATE TABLE IF NOT EXISTS camionero_ruta")

    print("\n[ tarifas ]")
    run(conn, cur, """
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
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """, "CREATE TABLE IF NOT EXISTS tarifas")

    print("\n[ cotizaciones ]")
    run(conn, cur, """
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
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """, "CREATE TABLE IF NOT EXISTS cotizaciones")

    print("\n[ movimientos_viaje ]")
    run(conn, cur, """
        CREATE TABLE IF NOT EXISTS movimientos_viaje (
            id SERIAL PRIMARY KEY,
            viaje_id INTEGER,
            tipo TEXT,
            monto REAL DEFAULT 0,
            descripcion TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """, "CREATE TABLE IF NOT EXISTS movimientos_viaje")

    print("\n[ configuracion ]")
    run(conn, cur, """
        CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY,
            valor REAL NOT NULL,
            descripcion TEXT
        )
    """, "CREATE TABLE IF NOT EXISTS configuracion")
    for clave, valor, desc in [
        ("tarifa_km",                    1.5,  "Tarifa por km cobrada al camionero (USD/km)"),
        ("margen_combustible_divisor",   2.0,  "Divisor para calcular combustible: pago_camionero / divisor"),
        ("multiplicador_pago_camionero", 2.5,  "Multiplicador para estimar precio cliente desde pago camionero"),
        ("minimo_km_garantizado",      120.0,  "Km mínimo garantizado para liquidación"),
        ("minimo_pago_usd",            150.0,  "Pago mínimo garantizado al camionero en USD"),
        ("comision_mercatoria_porcentaje", 20.0, "Porcentaje de comisión de Mercatoria sobre precio cliente"),
    ]:
        run(conn, cur,
            f"INSERT INTO configuracion (clave, valor, descripcion) VALUES ('{clave}', {valor}, '{desc}') ON CONFLICT (clave) DO NOTHING",
            f"seed: {clave}")

    print("\n[ configuracion_texto ]")
    run(conn, cur, """
        CREATE TABLE IF NOT EXISTS configuracion_texto (
            clave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        )
    """, "CREATE TABLE IF NOT EXISTS configuracion_texto")

    print("\n[ reset_tokens ]")
    run(conn, cur, """
        CREATE TABLE IF NOT EXISTS reset_tokens (
            id SERIAL PRIMARY KEY,
            token TEXT UNIQUE,
            usuario TEXT,
            expira TEXT,
            usado INTEGER DEFAULT 0
        )
    """, "CREATE TABLE IF NOT EXISTS reset_tokens")

    print("\n[ auditoria ]")
    run(conn, cur, """
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
    """, "CREATE TABLE IF NOT EXISTS auditoria")

    print("\n[ notas_viaje ]")
    run(conn, cur, """
        CREATE TABLE IF NOT EXISTS notas_viaje (
            id SERIAL PRIMARY KEY,
            viaje_id INTEGER NOT NULL,
            usuario TEXT NOT NULL,
            texto TEXT NOT NULL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """, "CREATE TABLE IF NOT EXISTS notas_viaje")

    print("\n[ viaje_checklist ]")
    run(conn, cur, """
        CREATE TABLE IF NOT EXISTS viaje_checklist (
            id SERIAL PRIMARY KEY,
            viaje_id INTEGER NOT NULL,
            item TEXT NOT NULL,
            completado INTEGER DEFAULT 0,
            completado_por TEXT,
            fecha_completado TIMESTAMP
        )
    """, "CREATE TABLE IF NOT EXISTS viaje_checklist")

    print("\n[ incidencias ]")
    run(conn, cur, """
        CREATE TABLE IF NOT EXISTS incidencias (
            id SERIAL PRIMARY KEY,
            viaje_id INTEGER NOT NULL,
            categoria TEXT NOT NULL,
            descripcion TEXT,
            usuario TEXT,
            fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            estado TEXT DEFAULT 'Abierta'
        )
    """, "CREATE TABLE IF NOT EXISTS incidencias")

    # ── 8. Índices ────────────────────────────────────────────────────────────
    print("\n[ índices ]")
    indices = [
        ("idx_viajes_estado",        "viajes",     "estado"),
        ("idx_viajes_cliente_id",    "viajes",     "cliente_id"),
        ("idx_viajes_camionero_id",  "viajes",     "camionero_id"),
        ("idx_viajes_fecha_creacion","viajes",     "fecha_creacion"),
        ("idx_clientes_activo",      "clientes",   "activo"),
        ("idx_camioneros_estado",    "camioneros", "estado"),
        ("idx_auditoria_fecha",      "auditoria",  "fecha"),
    ]
    for nombre, tabla, col in indices:
        run(conn, cur,
            f"CREATE INDEX IF NOT EXISTS {nombre} ON {tabla}({col})",
            nombre)

    cur.close()
    conn.close()
    print("\n=== Migración v1.1 completada ===\n")


if __name__ == "__main__":
    main()
