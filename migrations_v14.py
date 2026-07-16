"""
Migración v1.4 para PostgreSQL (producción).
Cadena vehiculo -> tipo: backfill de tipo_vehiculo_id por nombre, y
eliminación de catalogo_tipo_transporte (duplicado desconectado de
tipos_vehiculo).
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


def aplicar_migraciones_v14():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("[migrations_v14] DATABASE_URL no configurada — omitiendo.")
        return
    try:
        conn = psycopg2.connect(database_url)
    except Exception as e:
        print(f"[migrations_v14] No se pudo conectar a la BD: {e}")
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
    print("\n=== migrations_v14.py — Mercatoria Truck ===\n")

    print("[ backfill vehiculos.tipo_vehiculo_id por nombre ]")
    # Unico e idempotente: solo toca filas sin FK todavia, nunca pisa una ya
    # resuelta. Lo que no matchea por nombre queda igual (no empeora nada).
    run(conn, cur, """
        UPDATE vehiculos SET tipo_vehiculo_id = (
            SELECT id FROM tipos_vehiculo WHERE LOWER(tipos_vehiculo.nombre) = LOWER(vehiculos.tipo)
        ) WHERE tipo_vehiculo_id IS NULL AND tipo IS NOT NULL
    """, "backfill tipo_vehiculo_id")

    print("\n[ eliminar catalogo_tipo_transporte (duplicado desconectado) ]")
    run(conn, cur, "DROP TABLE IF EXISTS catalogo_tipo_transporte", "DROP TABLE catalogo_tipo_transporte")

    cur.close()
    conn.close()
    print("\n=== Migración v1.4 completada ===\n")


if __name__ == "__main__":
    main()
