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

    cur.close()
    conn.close()
    print("\n=== Migración v1.2 completada ===\n")


if __name__ == "__main__":
    main()
