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
    """
    Devuelve un dict con todos los valores económicos del viaje.
    Retorna None si no existe tarifa para esa combinación.
    """
    tarifa = get_tarifa(ruta_id, tipo_vehiculo_id)
    if not tarifa:
        return None

    precio_cliente   = tarifa["precio_cliente"]
    pago_camionero   = tarifa["pago_camionero"]
    combustible      = tarifa["combustible_estimado"] or 0
    km               = tarifa["km_oficiales"]
    beneficio        = round(precio_cliente - pago_camionero - combustible, 2)

    return {
        "ruta_id":            ruta_id,
        "tipo_vehiculo_id":   tipo_vehiculo_id,
        "origen":             tarifa["origen"],
        "destino":            tarifa["destino"],
        "tipo_vehiculo":      tarifa["tipo_vehiculo"],
        "km":                 km,
        "precio_calculado":   precio_cliente,
        "precio_final":       precio_cliente,
        "pago_camionero":     pago_camionero,
        "combustible_estimado": combustible,
        "beneficio_estimado": beneficio,
    }


def guardar_cotizacion(datos, cliente_id, usuario_id,
                       precio_final_override=None, motivo=None):
    """
    Persiste la cotización. Si el operador modifica el precio,
    registra el override con trazabilidad completa.
    """
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