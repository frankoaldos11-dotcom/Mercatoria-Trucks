from database import conectar
from db_config import USE_POSTGRES


def ph():
    return "%s" if USE_POSTGRES else "?"


# ── RUTAS ────────────────────────────────────────────────────────────────────

def get_all_rutas():
    con = conectar()
    cur = con.cursor()
    cur.execute("SELECT * FROM rutas WHERE activa = 1 ORDER BY origen, destino")
    rows = cur.fetchall()
    con.close()
    return rows


def get_ruta(ruta_id):
    con = conectar()
    cur = con.cursor()
    cur.execute(f"SELECT * FROM rutas WHERE id = {ph()}", (ruta_id,))
    row = cur.fetchone()
    con.close()
    return row


def crear_ruta(origen, destino, zona, km):
    con = conectar()
    cur = con.cursor()
    cur.execute(f"""
        INSERT INTO rutas (origen, destino, zona, km_oficiales)
        VALUES ({ph()}, {ph()}, {ph()}, {ph()})
    """, (origen.strip(), destino.strip(), zona.strip(), float(km)))
    con.commit()
    con.close()


def ruta_existe(origen, destino):
    con = conectar()
    cur = con.cursor()
    cur.execute(f"""
        SELECT id FROM rutas
        WHERE LOWER(origen) = LOWER({ph()}) AND LOWER(destino) = LOWER({ph()})
    """, (origen.strip(), destino.strip()))
    row = cur.fetchone()
    con.close()
    return row


# ── TIPOS DE VEHÍCULO ────────────────────────────────────────────────────────

def get_all_tipos_vehiculo():
    con = conectar()
    cur = con.cursor()
    cur.execute("SELECT * FROM tipos_vehiculo WHERE activo = 1 ORDER BY nombre")
    rows = cur.fetchall()
    con.close()
    return rows


def crear_tipo_vehiculo(nombre, descripcion, capacidad_ton):
    con = conectar()
    cur = con.cursor()
    cur.execute(f"""
        INSERT INTO tipos_vehiculo (nombre, descripcion, capacidad_ton)
        VALUES ({ph()}, {ph()}, {ph()})
    """, (nombre.strip(), descripcion.strip(), float(capacidad_ton) if capacidad_ton else None))
    con.commit()
    con.close()


# ── TARIFAS ──────────────────────────────────────────────────────────────────

def get_all_tarifas():
    con = conectar()
    cur = con.cursor()
    cur.execute("""
        SELECT t.id, r.origen, r.destino, r.km_oficiales,
               tv.nombre AS tipo_vehiculo,
               t.precio_cliente, t.pago_camionero,
               t.precio_km_cliente,
               t.combustible_estimado, t.vigencia_desde, t.vigencia_hasta, t.activa
        FROM tarifas t
        JOIN rutas r ON t.ruta_id = r.id
        JOIN tipos_vehiculo tv ON t.tipo_vehiculo_id = tv.id
        ORDER BY r.origen, r.destino, tv.nombre
    """)
    rows = cur.fetchall()
    con.close()
    return rows


def get_tarifa(ruta_id, tipo_vehiculo_id):
    con = conectar()
    cur = con.cursor()
    cur.execute(f"""
        SELECT t.*, r.km_oficiales, r.origen, r.destino, tv.nombre AS tipo_vehiculo
        FROM tarifas t
        JOIN rutas r ON t.ruta_id = r.id
        JOIN tipos_vehiculo tv ON t.tipo_vehiculo_id = tv.id
        WHERE t.ruta_id = {ph()} AND t.tipo_vehiculo_id = {ph()} AND t.activa = 1
    """, (ruta_id, tipo_vehiculo_id))
    row = cur.fetchone()
    con.close()
    return row


def crear_tarifa(ruta_id, tipo_vehiculo_id, precio_cliente, pago_camionero,
                 combustible_estimado, vigencia_desde, vigencia_hasta):
    con = conectar()
    cur = con.cursor()
    ruta = get_ruta(ruta_id)
    km = ruta["km_oficiales"] if ruta else 1

    precio_km_cliente = round(float(precio_cliente) / km, 4) if km else 0
    precio_km_camionero = round(float(pago_camionero) / km, 4) if km else 0

    cur.execute(f"""
        INSERT INTO tarifas (
            ruta_id, tipo_vehiculo_id,
            precio_cliente, pago_camionero,
            precio_km_cliente, precio_km_camionero,
            combustible_estimado, vigencia_desde, vigencia_hasta
        ) VALUES ({ph()}, {ph()}, {ph()}, {ph()}, {ph()}, {ph()}, {ph()}, {ph()}, {ph()})
    """, (
        ruta_id, tipo_vehiculo_id,
        float(precio_cliente), float(pago_camionero),
        precio_km_cliente, precio_km_camionero,
        float(combustible_estimado) if combustible_estimado else None,
        vigencia_desde or None, vigencia_hasta or None
    ))
    con.commit()
    con.close()


# ── MOTOR DE COTIZACIÓN ──────────────────────────────────────────────────────

def cotizar(ruta_id, tipo_vehiculo_id):
    tarifa = get_tarifa(ruta_id, tipo_vehiculo_id)

    if not tarifa:
        return None

    precio_cliente = tarifa["precio_cliente"]
    pago_camionero = tarifa["pago_camionero"]
    combustible = tarifa["combustible_estimado"] or 0
    km = tarifa["km_oficiales"]
    beneficio = round(precio_cliente - pago_camionero - combustible, 2)

    return {
        "ruta_id": ruta_id,
        "tipo_vehiculo_id": tipo_vehiculo_id,
        "tarifa_id": tarifa["id"],
        "origen": tarifa["origen"],
        "destino": tarifa["destino"],
        "tipo_vehiculo": tarifa["tipo_vehiculo"],
        "km": km,
        "precio_calculado": precio_cliente,
        "precio_final": precio_cliente,
        "pago_camionero": pago_camionero,
        "combustible_estimado": combustible,
        "beneficio_estimado": beneficio,
    }


def guardar_cotizacion(datos, cliente_id, usuario_id,
                       precio_final_override=None, motivo=None):
    modificado = False
    precio_final = datos["precio_calculado"]

    if precio_final_override and float(precio_final_override) != float(datos["precio_calculado"]):
        modificado = True
        precio_final = float(precio_final_override)

    beneficio = round(precio_final - datos["pago_camionero"] - datos["combustible_estimado"], 2)

    con = conectar()
    cur = con.cursor()
    cur.execute(f"""
        INSERT INTO cotizaciones (
            cliente_id, ruta_id, tipo_vehiculo_id, km,
            precio_calculado, precio_final, pago_camionero,
            combustible_estimado, beneficio_estimado,
            modificado_manualmente, motivo_modificacion, usuario_modificacion,
            estado
        ) VALUES ({ph()}, {ph()}, {ph()}, {ph()}, {ph()}, {ph()}, {ph()}, {ph()}, {ph()}, {ph()}, {ph()}, {ph()}, 'borrador')
    """, (
        cliente_id, datos["ruta_id"], datos["tipo_vehiculo_id"], datos["km"],
        datos["precio_calculado"], precio_final, datos["pago_camionero"],
        datos["combustible_estimado"], beneficio,
        1 if modificado else 0, motivo if modificado else None,
        usuario_id if modificado else None
    ))
    cotizacion_id = cur.lastrowid
    con.commit()
    con.close()
    return cotizacion_id


def get_all_cotizaciones():
    con = conectar()
    cur = con.cursor()

    cur.execute("""
        SELECT
            c.id,
            cl.nombre AS cliente,
            r.origen,
            r.destino,
            tv.nombre AS tipo_vehiculo,
            c.precio_final,
            c.beneficio_estimado,
            c.estado
        FROM cotizaciones c
        LEFT JOIN clientes cl ON cl.id = c.cliente_id
        JOIN rutas r ON r.id = c.ruta_id
        JOIN tipos_vehiculo tv ON tv.id = c.tipo_vehiculo_id
        ORDER BY c.id DESC
    """)

    datos = cur.fetchall()
    con.close()
    return datos


def get_cotizacion_detalle(id):
    con = conectar()
    cur = con.cursor()

    cur.execute(f"""
        SELECT
            c.*,
            cl.nombre AS cliente_nombre,
            r.origen AS ruta_origen,
            r.destino AS ruta_destino,
            tv.nombre AS tipo_vehiculo_nombre
        FROM cotizaciones c
        LEFT JOIN clientes cl ON cl.id = c.cliente_id
        JOIN rutas r ON r.id = c.ruta_id
        JOIN tipos_vehiculo tv ON tv.id = c.tipo_vehiculo_id
        WHERE c.id = {ph()}
    """, (id,))

    dato = cur.fetchone()
    con.close()
    return dato


def actualizar_tarifa_km_ruta(ruta_id, tarifa_km):
    con = conectar()
    cur = con.cursor()
    val = float(tarifa_km) if tarifa_km not in (None, "", "null") else None
    cur.execute(f"UPDATE rutas SET tarifa_km = {ph()} WHERE id = {ph()}", (val, ruta_id))
    con.commit()
    con.close()


def get_camioneros_por_ruta(ruta_id):
    con = conectar()
    cur = con.cursor()
    cur.execute(f"""
        SELECT c.id, c.nombre, c.telefono, c.estado
        FROM camioneros c
        JOIN camionero_ruta cr ON cr.camionero_id = c.id
        WHERE cr.ruta_id = {ph()} AND c.activo = 1
        ORDER BY c.nombre
    """, (ruta_id,))
    rows = cur.fetchall()
    con.close()
    return rows


def get_all_camioneros_activos():
    con = conectar()
    cur = con.cursor()
    cur.execute("SELECT id, nombre, estado FROM camioneros WHERE activo = 1 ORDER BY nombre")
    rows = cur.fetchall()
    con.close()
    return rows


def asignar_camionero_a_ruta(ruta_id, camionero_id):
    con = conectar()
    cur = con.cursor()
    if USE_POSTGRES:
        cur.execute(
            f"INSERT INTO camionero_ruta (ruta_id, camionero_id) VALUES ({ph()}, {ph()}) ON CONFLICT DO NOTHING",
            (ruta_id, camionero_id)
        )
    else:
        cur.execute(
            f"INSERT OR IGNORE INTO camionero_ruta (ruta_id, camionero_id) VALUES ({ph()}, {ph()})",
            (ruta_id, camionero_id)
        )
    con.commit()
    con.close()


def desasociar_camionero_de_ruta(ruta_id, camionero_id):
    con = conectar()
    cur = con.cursor()
    cur.execute(
        f"DELETE FROM camionero_ruta WHERE ruta_id = {ph()} AND camionero_id = {ph()}",
        (ruta_id, camionero_id)
    )
    con.commit()
    con.close()


def get_rutas_por_camionero(camionero_id):
    con = conectar()
    cur = con.cursor()
    cur.execute(f"""
        SELECT r.id, r.origen, r.destino, r.km_oficiales, r.zona
        FROM rutas r
        JOIN camionero_ruta cr ON cr.ruta_id = r.id
        WHERE cr.camionero_id = {ph()} AND r.activa = 1
        ORDER BY r.origen, r.destino
    """, (camionero_id,))
    rows = cur.fetchall()
    con.close()
    return rows


def convertir_cotizacion_en_viaje(cotizacion_id):
    con = conectar()
    cur = con.cursor()

    if USE_POSTGRES:
        cur.execute("""
            SELECT column_name AS name FROM information_schema.columns
            WHERE table_name = 'viajes'
        """)
    else:
        cur.execute("PRAGMA table_info(viajes)")
    columnas_viajes = [col["name"] for col in cur.fetchall()]

    cur.execute(f"""
        SELECT
            c.*,
            cl.nombre AS cliente_nombre,
            r.origen AS origen_ruta,
            r.destino AS destino_ruta,
            tv.nombre AS tipo_vehiculo_nombre,
            t.id AS tarifa_id
        FROM cotizaciones c
        LEFT JOIN clientes cl ON cl.id = c.cliente_id
        JOIN rutas r ON r.id = c.ruta_id
        JOIN tipos_vehiculo tv ON tv.id = c.tipo_vehiculo_id
        LEFT JOIN tarifas t
            ON t.ruta_id = c.ruta_id
            AND t.tipo_vehiculo_id = c.tipo_vehiculo_id
            AND t.activa = 1
        WHERE c.id = {ph()}
    """, (cotizacion_id,))

    c = cur.fetchone()

    if not c:
        con.close()
        return None

    if "cotizacion_id" in columnas_viajes:
        cur.execute(f"SELECT id FROM viajes WHERE cotizacion_id = {ph()}", (cotizacion_id,))
        viaje_existente = cur.fetchone()

        if viaje_existente:
            cur.execute(f"""
                UPDATE cotizaciones
                SET estado = 'convertida'
                WHERE id = {ph()}
            """, (cotizacion_id,))
            con.commit()
            con.close()
            return viaje_existente["id"]

    cliente_nombre = c["cliente_nombre"] or ""
    origen = c["origen_ruta"]
    destino = c["destino_ruta"]

    precio_calculado = c["precio_calculado"] or 0
    precio_final = c["precio_final"] or precio_calculado
    pago_camionero = c["pago_camionero"] or 0
    combustible = c["combustible_estimado"] or 0
    beneficio = c["beneficio_estimado"]

    if beneficio is None:
        beneficio = round(float(precio_final) - float(pago_camionero) - float(combustible), 2)

    posibles = {
        "cliente": cliente_nombre,
        "cliente_id": c["cliente_id"],
        "ruta_id": c["ruta_id"],
        "tarifa_id": c["tarifa_id"],
        "tipo_vehiculo_id": c["tipo_vehiculo_id"],
        "origen": origen,
        "destino": destino,
        "km": c["km"],
        "kilometros": c["km"],

        "precio": precio_final,
        "precio_cliente": precio_final,
        "precio_calculado": precio_calculado,
        "precio_final": precio_final,

        "combustible": combustible,
        "combustible_estimado": combustible,

        "pago_camionero": pago_camionero,

        "beneficio": beneficio,
        "beneficio_estimado": beneficio,

        "cotizacion_id": c["id"],
        "estado": "pendiente",
        "observaciones": f"Viaje generado desde cotización #{c['id']}",
    }

    datos = {}

    for columna, valor in posibles.items():
        if columna in columnas_viajes:
            datos[columna] = valor

    campos = ", ".join(datos.keys())
    placeholders = ", ".join([ph()] * len(datos))
    valores = list(datos.values())

    cur.execute(
        f"INSERT INTO viajes ({campos}) VALUES ({placeholders})",
        valores
    )

    viaje_id = cur.lastrowid

    cur.execute(f"""
        UPDATE cotizaciones
        SET estado = 'convertida'
        WHERE id = {ph()}
    """, (cotizacion_id,))

    con.commit()
    con.close()

    return viaje_id
