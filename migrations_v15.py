"""
Migración v1.5 para PostgreSQL (producción).
Litros de combustible confirmados: nueva columna persistida en viajes,
usada por la confirmación de combustible (en litros, no dólares) y por
la Orden de Carga (saldo de combustible a entregar al transportista).
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


def aplicar_migraciones_v15():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("[migrations_v15] DATABASE_URL no configurada — omitiendo.")
        return
    try:
        conn = psycopg2.connect(database_url)
    except Exception as e:
        print(f"[migrations_v15] No se pudo conectar a la BD: {e}")
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
    print("\n=== migrations_v15.py — Mercatoria Truck ===\n")

    print("[ litros de combustible confirmados ]")
    run(conn, cur, "ALTER TABLE viajes ADD COLUMN IF NOT EXISTS litros_combustible REAL", "litros_combustible")

    cur.close()
    conn.close()
    print("\n=== Migración v1.5 completada ===\n")


if __name__ == "__main__":
    main()
