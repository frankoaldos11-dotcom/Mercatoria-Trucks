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


def obtener_precio_litro(zona):
    """Punto único de verdad para el precio del litro de combustible.

    Toda consulta de precio en el sistema debe pasar por acá, no por lecturas
    directas a zonas_combustible desde otros archivos — el día que se integre
    con el sistema Fuel vía API para leer precios de compra reales, se
    reemplaza el CUERPO de esta función (y de acá abajo la política de
    fallback si la API falla) sin tocar nada de lo que la llama.

    Devuelve (precio: float, fuente: str) — fuente es "zona" si se encontró
    un precio real configurado para esa zona, "default_global" si se usó el
    precio de reserva de configuracion, o "sin_dato" si ni siquiera ese
    default está configurado (nunca lanza excepción, nunca devuelve None).
    """
    if zona:
        con = conectar()
        cur = con.cursor()
        cur.execute(
            f"SELECT precio_litro FROM zonas_combustible "
            f"WHERE LOWER(nombre) = LOWER({ph()}) AND activo = 1",
            (zona.strip(),)
        )
        row = cur.fetchone()
        con.close()
        if row and row["precio_litro"]:
            return float(row["precio_litro"]), "zona"

    # Fallback: precio_litro_default en configuracion — placeholder sembrado en
    # 0.0 a propósito (ver migraciones.py/migrations_v13.py), para que un costo
    # calculado con este fallback sea visiblemente sospechoso en vez de un
    # número inventado que parezca válido.
    cfg = get_configuracion()
    default = cfg.get("precio_litro_default")
    if default:
        return float(default), "default_global"
    return 0.0, "sin_dato"


def obtener_divisor_consumo(tipo_vehiculo_id):
    """Punto único de verdad para el divisor de consumo (km por litro) de un
    tipo de vehículo. Devuelve (divisor: float, fuente: str) — fuente es
    "tipo_vehiculo" si el viaje tiene un tipo con divisor propio configurado,
    o "default_global" si se usó el fallback (viaje sin tipo asignado, o tipo
    sin divisor propio)."""
    if tipo_vehiculo_id:
        con = conectar()
        cur = con.cursor()
        cur.execute(
            f"SELECT divisor_consumo FROM tipos_vehiculo WHERE id = {ph()} AND activo = 1",
            (tipo_vehiculo_id,)
        )
        row = cur.fetchone()
        con.close()
        if row and row["divisor_consumo"]:
            return float(row["divisor_consumo"]), "tipo_vehiculo"

    # Fallback: margen_combustible_divisor — antes era EL divisor único global,
    # ahora es solo la reserva para cuando el viaje no tiene tipo de vehículo
    # asignado o su tipo no tiene divisor propio (hoy el caso más común, ver
    # plan de esta tarea — viajes.tipo_vehiculo_id no se está poblando todavía
    # en la creación/asignación de viajes).
    cfg = get_configuracion()
    return float(cfg.get("margen_combustible_divisor", 2.0)), "default_global"


def calcular_liquidacion(viaje_id):
    con = conectar()
    cur = con.cursor()

    cur.execute(f"SELECT * FROM viajes WHERE id = {ph()}", (viaje_id,))
    viaje = cur.fetchone()

    ruta_tarifa_km = None
    ruta_zona = None
    km_ruta = 0.0
    if viaje and _col_exists(viaje, "ruta_id") and viaje["ruta_id"]:
        try:
            cur.execute(f"SELECT tarifa_km, km_oficiales, zona FROM rutas WHERE id = {ph()}", (viaje["ruta_id"],))
            ruta = cur.fetchone()
            if ruta and ruta["tarifa_km"] is not None:
                ruta_tarifa_km = float(ruta["tarifa_km"])
            if ruta and ruta["km_oficiales"]:
                km_ruta = float(ruta["km_oficiales"])
            if ruta:
                ruta_zona = ruta["zona"]
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error calculando tarifa/km de ruta para viaje {viaje_id}: {e}")

    con.close()

    if not viaje:
        return None

    cfg = get_configuracion()

    tarifa_km_global          = cfg.get("tarifa_km", 1.5)
    tarifa_km_fuente          = "ruta" if ruta_tarifa_km is not None else "global"
    tarifa_km                 = ruta_tarifa_km if ruta_tarifa_km is not None else tarifa_km_global
    multiplicador_camionero   = cfg.get("multiplicador_pago_camionero", 2.5)
    minimo_km                 = cfg.get("minimo_km_garantizado", 120.0)
    minimo_pago               = cfg.get("minimo_pago_usd", 150.0)
    comision_pct              = cfg.get("comision_mercatoria_porcentaje", 20.0)

    tipo_vehiculo_id = viaje["tipo_vehiculo_id"] if _col_exists(viaje, "tipo_vehiculo_id") else None
    divisor_consumo, divisor_fuente = obtener_divisor_consumo(tipo_vehiculo_id)

    # Viaje multi-tramo: km total y precio cliente se calculan sumando cada tramo;
    # litros/combustible también, cada tramo con su propia zona (ver tramos_service.py)
    totales_tramos = calcular_totales_tramos(viaje_id, divisor_consumo, obtener_precio_litro)

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

    # Combustible = litros estimados (km / divisor de consumo del tipo de vehículo)
    # × precio por litro de la zona de origen de la ruta. Multi-tramo ya viene
    # sumado tramo por tramo desde calcular_totales_tramos().
    if totales_tramos and "litros_total" in totales_tramos:
        litros_combustible = totales_tramos["litros_total"]
        combustible = totales_tramos["combustible_total"]
        precio_litro_fuente = totales_tramos["precio_litro_fuente"]
    else:
        precio_litro, precio_litro_fuente = obtener_precio_litro(ruta_zona)
        litros_combustible = km_real / divisor_consumo if divisor_consumo else 0
        combustible = litros_combustible * precio_litro

    # Precio cliente: preferir el cobro real (monto_cobrado) si ya se registró;
    # si no, caer al precio teórico / tramos / estimado, como hasta ahora
    monto_cobrado = viaje["monto_cobrado"] if _col_exists(viaje, "monto_cobrado") else None
    if monto_cobrado is not None:
        precio_cliente = float(monto_cobrado)
    else:
        precio_cliente = float(
            viaje["precio_final"] or viaje["precio"] or 0
        ) if _col_exists(viaje, "precio_final") else 0
        if precio_cliente == 0 and totales_tramos:
            precio_cliente = totales_tramos["precio_cliente_total"]
        if precio_cliente == 0:
            precio_cliente = pago_camionero * multiplicador_camionero

    comision_mercatoria = precio_cliente * comision_pct / 100
    utilidad_mercatoria = comision_mercatoria

    return {
        "km_real":             round(km_real, 2),
        "km_liquidable":       round(km_liquidable, 2),
        "combustible":         round(combustible, 2),
        "litros_combustible":  round(litros_combustible, 1),
        "precio_litro_fuente": precio_litro_fuente,
        "divisor_consumo":     divisor_consumo,
        "divisor_fuente":      divisor_fuente,
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
