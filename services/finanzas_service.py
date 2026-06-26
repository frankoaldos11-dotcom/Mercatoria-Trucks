from database import conectar


def get_configuracion():
    con = conectar()
    cur = con.cursor()
    cur.execute("SELECT clave, valor FROM configuracion")
    rows = cur.fetchall()
    con.close()
    return {row["clave"]: row["valor"] for row in rows}


def guardar_configuracion(parametros: dict):
    con = conectar()
    cur = con.cursor()
    for clave, valor in parametros.items():
        cur.execute(
            "UPDATE configuracion SET valor = ? WHERE clave = ?",
            (float(valor), clave)
        )
    con.commit()
    con.close()


def calcular_liquidacion(viaje_id):
    con = conectar()
    cur = con.cursor()

    cur.execute("SELECT * FROM viajes WHERE id = ?", (viaje_id,))
    viaje = cur.fetchone()
    con.close()

    if not viaje:
        return None

    cfg = get_configuracion()

    tarifa_km                 = cfg.get("tarifa_km", 1.5)
    margen_divisor            = cfg.get("margen_combustible_divisor", 2.0)
    multiplicador_camionero   = cfg.get("multiplicador_pago_camionero", 2.5)
    minimo_km                 = cfg.get("minimo_km_garantizado", 120.0)
    minimo_pago               = cfg.get("minimo_pago_usd", 150.0)
    comision_pct              = cfg.get("comision_mercatoria_porcentaje", 20.0)

    # km real del viaje (buscar en columnas posibles)
    km_real = float(viaje["km"] or viaje["kilometros"] or 0) if _col_exists(viaje, "km") else 0

    km_liquidable = max(km_real, minimo_km) if km_real > 0 else minimo_km

    pago_camionero_calc = km_liquidable * tarifa_km
    pago_camionero = max(pago_camionero_calc, minimo_pago)

    combustible = pago_camionero / margen_divisor if margen_divisor else 0

    # Precio cliente: usar el registrado en el viaje o estimar con multiplicador
    precio_cliente = float(
        viaje["precio_final"] or viaje["precio"] or 0
    ) if _col_exists(viaje, "precio_final") else 0
    if precio_cliente == 0:
        precio_cliente = pago_camionero * multiplicador_camionero

    comision_mercatoria = precio_cliente * comision_pct / 100
    utilidad_mercatoria = precio_cliente - pago_camionero - combustible - comision_mercatoria

    return {
        "km_real":             round(km_real, 2),
        "km_liquidable":       round(km_liquidable, 2),
        "combustible":         round(combustible, 2),
        "pago_camionero":      round(pago_camionero, 2),
        "precio_cliente":      round(precio_cliente, 2),
        "comision_mercatoria": round(comision_mercatoria, 2),
        "utilidad_mercatoria": round(utilidad_mercatoria, 2),
        "minimo_aplicado":     km_real < minimo_km or km_real == 0,
        "config":              cfg,
    }


def _col_exists(row, col):
    try:
        _ = row[col]
        return True
    except (IndexError, KeyError):
        return False
