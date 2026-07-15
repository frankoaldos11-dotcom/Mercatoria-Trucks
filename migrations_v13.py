"""
Migración v1.3 para PostgreSQL (producción).
Costo de combustible real: zonas de precio + divisor de consumo por tipo de vehículo.
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


def aplicar_migraciones_v13():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("[migrations_v13] DATABASE_URL no configurada — omitiendo.")
        return
    try:
        conn = psycopg2.connect(database_url)
    except Exception as e:
        print(f"[migrations_v13] No se pudo conectar a la BD: {e}")
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
    print("\n=== migrations_v13.py — Mercatoria Truck ===\n")

    print("[ zonas de combustible ]")
    run(conn, cur, """
        CREATE TABLE IF NOT EXISTS zonas_combustible (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL UNIQUE,
            precio_litro REAL NOT NULL,
            activo INTEGER DEFAULT 1
        )
    """, "CREATE TABLE zonas_combustible")

    # Placeholder: precios iniciales a definir por el área financiera.
    for _zona, _precio in [("Occidente", 2.6), ("Oriente", 3.15)]:
        run(conn, cur,
            f"INSERT INTO zonas_combustible (nombre, precio_litro) VALUES ('{_zona}', {_precio}) ON CONFLICT (nombre) DO NOTHING",
            f"seed zona {_zona}")

    print("\n[ divisor de consumo por tipo de vehiculo ]")
    # Placeholder: mismo divisor global de siempre (2.0) para no cambiar el
    # comportamiento hasta que el área financiera defina el divisor real por tipo.
    run(conn, cur, "ALTER TABLE tipos_vehiculo ADD COLUMN IF NOT EXISTS divisor_consumo REAL DEFAULT 2.0", "divisor_consumo")
    run(conn, cur, "UPDATE tipos_vehiculo SET divisor_consumo = 2.0 WHERE divisor_consumo IS NULL", "backfill divisor_consumo")

    print("\n[ precio de litro de reserva ]")
    # Placeholder: fallback cuando una zona no tiene precio configurado — 0.0 a
    # propósito, para que sea visiblemente sospechoso en vez de un número inventado.
    run(conn, cur, """
        INSERT INTO configuracion (clave, valor, descripcion)
        VALUES ('precio_litro_default', 0.0, 'Precio/litro de reserva cuando la zona de la ruta no tiene precio configurado')
        ON CONFLICT (clave) DO NOTHING
    """, "seed precio_litro_default")

    cur.close()
    conn.close()
    print("\n=== Migración v1.3 completada ===\n")


if __name__ == "__main__":
    main()
