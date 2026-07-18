"""
Migración v1.6 para PostgreSQL (producción).
Motivo de solicitud de eliminación: nueva columna en solicitudes_eliminacion,
para que el operador/PM pueda explicar por qué pide borrar un viaje (u otra
entidad) antes de que el admin apruebe o rechace.
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


def aplicar_migraciones_v16():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("[migrations_v16] DATABASE_URL no configurada — omitiendo.")
        return
    try:
        conn = psycopg2.connect(database_url)
    except Exception as e:
        print(f"[migrations_v16] No se pudo conectar a la BD: {e}")
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
    print("\n=== migrations_v16.py — Mercatoria Truck ===\n")

    print("[ motivo de solicitud de eliminación ]")
    run(conn, cur, "ALTER TABLE solicitudes_eliminacion ADD COLUMN IF NOT EXISTS motivo TEXT", "motivo")

    cur.close()
    conn.close()
    print("\n=== Migración v1.6 completada ===\n")


if __name__ == "__main__":
    main()
