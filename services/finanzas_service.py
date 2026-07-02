from database import conectar
from db_config import USE_POSTGRES
from services.tramos_service import calcular_totales_tramos


def ph():
    return "%s" if USE_POSTGRES else "?"


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
        if USE_POSTGRES:
            cur.execute(
                "INSERT INTO configuracion (clave, valor) VALUES (%s, %s) "
                "ON CONFLICT (clave) DO UPDATE SET valor = EXCLUDED.valor",
                (clave, float(valor))
            )
        else:
            cur.execute(
                "INSERT INTO configuracion (clave, valor) VALUES (?, ?) "
                "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
                (clave, float(valor))
            )
    con.commit()
    con.close()


def calcular_liquidacion(viaje_id):
    con = conectar()
    cur = con.cursor()

    cur.execute(f"SELECT * FROM viajes WHERE id = {ph()}", (viaje_id,))
    viaje = cur.fetchone()

    ruta_tarifa_km = None
    km_ruta = 0.0
    if viaje and _col_exists(viaje, "ruta_id") and viaje["ruta_id"]:
        try:
            cur.execute(f"SELECT tarifa_km, km_oficiales FROM rutas WHERE id = {ph()}", (viaje["ruta_id"],))
            ruta = cur.fetchone()
            if ruta and ruta["tarifa_km"] is not None:
                ruta_tarifa_km = float(ruta["tarifa_km"])
            if ruta and ruta["km_oficiales"]:
                km_ruta = float(ruta["km_oficiales"])
        except Exception:
            pass

    con.close()

    if not viaje:
        return None

    cfg = get_configuracion()

    tarifa_km_global          = cfg.get("tarifa_km", 1.5)
    tarifa_km_fuente          = "ruta" if ruta_tarifa_km is not None else "global"
    tarifa_km                 = ruta_tarifa_km if ruta_tarifa_km is not None else tarifa_km_global
    margen_divisor            = cfg.get("margen_combustible_divisor", 2.0)
    multiplicador_camionero   = cfg.get("multiplicador_pago_camionero", 2.5)
    minimo_km                 = cfg.get("minimo_km_garantizado", 120.0)
    minimo_pago               = cfg.get("minimo_pago_usd", 150.0)
    comision_pct              = cfg.get("comision_mercatoria_porcentaje", 20.0)

    # Viaje multi-tramo: km total y precio cliente se calculan sumando cada tramo
    totales_tramos = calcular_totales_tramos(viaje_id)

    # km real del viaje (buscar en columnas posibles; usar km_oficiales de la ruta como fallback)
    km_real = float(viaje["km"] or viaje["kilometros"] or 0) if _col_exists(viaje, "km") else 0
    if km_real == 0 and km_ruta > 0:
        km_real = km_ruta
    if totales_tramos:
        km_real = totales_tramos["km_total"]
        tarifa_km_fuente = "tramos"

    km_liquidable = max(km_real, minimo_km) if km_real > 0 else minimo_km

    pago_camionero_calc = km_liquidable * tarifa_km
    pago_camionero = max(pago_camionero_calc, minimo_pago)

    combustible = pago_camionero / margen_divisor if margen_divisor else 0

    # Precio cliente: usar el registrado en el viaje, o sumar tramos, o estimar con multiplicador
    precio_cliente = float(
        viaje["precio_final"] or viaje["precio"] or 0
    ) if _col_exists(viaje, "precio_final") else 0
    if precio_cliente == 0 and totales_tramos:
        precio_cliente = totales_tramos["precio_cliente_total"]
    if precio_cliente == 0:
        precio_cliente = pago_camionero * multiplicador_camionero

    comision_mercatoria = precio_cliente * comision_pct / 100
    utilidad_mercatoria = precio_cliente - pago_camionero - combustible - comision_mercatoria

    return {
        "km_real":             round(km_real, 2),
        "km_liquidable":       round(km_liquidable, 2),
        "combustible":         round(combustible, 2),
        "litros_combustible":  round(km_real / margen_divisor, 1) if margen_divisor else 0,
        "pago_camionero":      round(pago_camionero, 2),
        "precio_cliente":      round(precio_cliente, 2),
        "comision_mercatoria": round(comision_mercatoria, 2),
        "utilidad_mercatoria": round(utilidad_mercatoria, 2),
        "minimo_aplicado":     km_real < minimo_km or km_real == 0,
        "tarifa_km":           tarifa_km,
        "tarifa_km_fuente":    tarifa_km_fuente,
        "config":              cfg,
    }


def _col_exists(row, col):
    try:
        _ = row[col]
        return True
    except (IndexError, KeyError):
        return False
