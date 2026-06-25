from database import conectar


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
    cur.execute("SELECT * FROM rutas WHERE id = ?", (ruta_id,))
    row = cur.fetchone()
    con.close()
    return row


def crear_ruta(origen, destino, zona, km):
    con = conectar()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO rutas (origen, destino, zona, km_oficiales)
        VALUES (?, ?, ?, ?)
    """, (origen.strip(), destino.strip(), zona.strip(), float(km)))
    con.commit()
    con.close()


def ruta_existe(origen, destino):
    con = conectar()
    cur = con.cursor()
    cur.execute("""
        SELECT id FROM rutas
        WHERE LOWER(origen) = LOWER(?) AND LOWER(destino) = LOWER(?)
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
    cur.execute("""
        INSERT INTO tipos_vehiculo (nombre, descripcion, capacidad_ton)
        VALUES (?, ?, ?)
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
    cur.execute("""
        SELECT t.*, r.km_oficiales, r.origen, r.destino, tv.nombre AS tipo_vehiculo
        FROM tarifas t
        JOIN rutas r ON t.ruta_id = r.id
        JOIN tipos_vehiculo tv ON t.tipo_vehiculo_id = tv.id
        WHERE t.ruta_id = ? AND t.tipo_vehiculo_id = ? AND t.activa = 1
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

    cur.execute("""
        INSERT INTO tarifas (
            ruta_id, tipo_vehiculo_id,
            precio_cliente, pago_camionero,
            precio_km_cliente, precio_km_camionero,
            combustible_estimado, vigencia_desde, vigencia_hasta
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    cur.execute("""
        INSERT INTO cotizaciones (
            cliente_id, ruta_id, tipo_vehiculo_id, km,
            precio_calculado, precio_final, pago_camionero,
            combustible_estimado, beneficio_estimado,
            modificado_manualmente, motivo_modificacion, usuario_modificacion,
            estado
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'borrador')
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

    cur.execute("""
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
        WHERE c.id = ?
    """, (id,))

    dato = cur.fetchone()
    con.close()
    return dato


def convertir_cotizacion_en_viaje(cotizacion_id):
    con = conectar()
    cur = con.cursor()

    cur.execute("PRAGMA table_info(viajes)")
    columnas_viajes = [col["name"] for col in cur.fetchall()]

    cur.execute("""
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
        WHERE c.id = ?
    """, (cotizacion_id,))

    c = cur.fetchone()

    if not c:
        con.close()
        return None

    if "cotizacion_id" in columnas_viajes:
        cur.execute("SELECT id FROM viajes WHERE cotizacion_id = ?", (cotizacion_id,))
        viaje_existente = cur.fetchone()

        if viaje_existente:
            cur.execute("""
                UPDATE cotizaciones
                SET estado = 'convertida'
                WHERE id = ?
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
    placeholders = ", ".join(["?"] * len(datos))
    valores = list(datos.values())

    cur.execute(
        f"INSERT INTO viajes ({campos}) VALUES ({placeholders})",
        valores
    )

    viaje_id = cur.lastrowid

    cur.execute("""
        UPDATE cotizaciones
        SET estado = 'convertida'
        WHERE id = ?
    """, (cotizacion_id,))

    con.commit()
    con.close()

    return viaje_id