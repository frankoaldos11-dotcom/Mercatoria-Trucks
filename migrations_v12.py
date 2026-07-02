"""
Migración v1.2 para PostgreSQL (producción).
Idempotente — safe de re-ejecutar.
"""
import os
import sys
import psycopg2
import psycopg2.extras


def run(conn, cur, sql, desc=""):
    try:
        cur.execute(sql)
        conn.commit()
        print(f"  OK  {desc or sql.strip()[:72]}")
    except Exception as e:
        conn.rollback()
        print(f"  --  {desc or ''}: {e}")


def aplicar_migraciones_v12():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("[migrations_v12] DATABASE_URL no configurada — omitiendo.")
        return
    try:
        conn = psycopg2.connect(database_url)
    except Exception as e:
        print(f"[migrations_v12] No se pudo conectar a la BD: {e}")
        return
    _ejecutar(conn)


def main():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("ERROR: DATABASE_URL no configurada.")
    conn = psycopg2.connect(database_url)
    _ejecutar(conn)


def _ejecutar(conn):
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    print("\n=== migrations_v12.py — Mercatoria Truck ===\n")

    print("[ papelera de reciclaje — camioneros ]")
    run(conn, cur, "ALTER TABLE camioneros ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP", "deleted_at")
    run(conn, cur, "ALTER TABLE camioneros ADD COLUMN IF NOT EXISTS deleted_by TEXT", "deleted_by")

    print("\n[ papelera de reciclaje — clientes ]")
    run(conn, cur, "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP", "deleted_at")
    run(conn, cur, "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS deleted_by TEXT", "deleted_by")

    print("\n[ papelera de reciclaje — viajes ]")
    run(conn, cur, "ALTER TABLE viajes ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP", "deleted_at")
    run(conn, cur, "ALTER TABLE viajes ADD COLUMN IF NOT EXISTS deleted_by TEXT", "deleted_by")

    print("\n[ campos camionero para puerto ]")
    run(conn, cur, "ALTER TABLE camioneros ADD COLUMN IF NOT EXISTS carnet_identidad TEXT", "carnet_identidad")
    run(conn, cur, "ALTER TABLE camioneros ADD COLUMN IF NOT EXISTS licencia_operativa TEXT", "licencia_operativa")
    run(conn, cur, "ALTER TABLE camioneros ADD COLUMN IF NOT EXISTS empresa TEXT", "empresa")

    print("\n[ chapa remolque en vehiculos ]")
    run(conn, cur, "ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS chapa_remolque TEXT", "chapa_remolque")

    print("\n[ cobro al cliente en viajes ]")
    run(conn, cur, "ALTER TABLE viajes ADD COLUMN IF NOT EXISTS forma_cobro TEXT", "forma_cobro")
    run(conn, cur, "ALTER TABLE viajes ADD COLUMN IF NOT EXISTS codigo_transaccion TEXT", "codigo_transaccion")
    run(conn, cur, "ALTER TABLE viajes ADD COLUMN IF NOT EXISTS comentario_cobro TEXT", "comentario_cobro")
    run(conn, cur, "ALTER TABLE viajes ADD COLUMN IF NOT EXISTS fecha_cobro TEXT", "fecha_cobro")
    run(conn, cur, "ALTER TABLE viajes ADD COLUMN IF NOT EXISTS monto_cobrado NUMERIC", "monto_cobrado")

    print("\n[ historial de cambios por viaje ]")
    run(conn, cur, """
        CREATE TABLE IF NOT EXISTS historial_viaje (
            id SERIAL PRIMARY KEY,
            viaje_id INTEGER NOT NULL,
            usuario TEXT NOT NULL,
            accion TEXT NOT NULL,
            detalle TEXT,
            fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (viaje_id) REFERENCES viajes(id)
        )
    """, "CREATE TABLE historial_viaje")

    print("\n[ solicitudes_eliminacion ]")
    run(conn, cur, """
        CREATE TABLE IF NOT EXISTS solicitudes_eliminacion (
            id SERIAL PRIMARY KEY,
            entidad TEXT NOT NULL,
            entidad_id INTEGER NOT NULL,
            nombre_entidad TEXT,
            solicitado_por TEXT NOT NULL,
            fecha_solicitud TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            estado TEXT DEFAULT 'Pendiente',
            revisado_por TEXT,
            fecha_revision TIMESTAMP
        )
    """, "CREATE TABLE solicitudes_eliminacion")

    print("\n[ viajes multi-tramo ]")
    run(conn, cur, """
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
    """, "CREATE TABLE viaje_tramos")
    run(conn, cur, "CREATE INDEX IF NOT EXISTS idx_viaje_tramos_viaje_id ON viaje_tramos(viaje_id)", "idx_viaje_tramos_viaje_id")

    cur.close()
    conn.close()
    print("\n=== Migración v1.2 completada ===\n")


if __name__ == "__main__":
    main()
