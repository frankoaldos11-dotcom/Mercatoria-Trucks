from database import conectar
from db_config import USE_POSTGRES


def ph():
    return "%s" if USE_POSTGRES else "?"


class ContinuidadError(ValueError):
    """El destino de un tramo no coincide con el origen del siguiente."""
    pass


def validar_continuidad(rutas):
    """rutas: lista ordenada de dicts/Row con 'origen' y 'destino'."""
    for i in range(len(rutas) - 1):
        destino_actual = (rutas[i]["destino"] or "").strip().lower()
        origen_siguiente = (rutas[i + 1]["origen"] or "").strip().lower()
        if destino_actual != origen_siguiente:
            raise ContinuidadError(
                f"El destino del tramo {i + 1} ({rutas[i]['destino']}) no coincide "
                f"con el origen del tramo {i + 2} ({rutas[i + 1]['origen']})"
            )


def _obtener_rutas_por_ids(cursor, ruta_ids):
    rutas_por_id = {}
    for ruta_id in ruta_ids:
        cursor.execute(f"SELECT * FROM rutas WHERE id = {ph()}", (ruta_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Ruta {ruta_id} no existe")
        rutas_por_id[ruta_id] = row
    return [rutas_por_id[rid] for rid in ruta_ids]


def crear_tramos_viaje(cursor, viaje_id, ruta_ids):
    """Inserta los tramos ordenados de un viaje ya creado. Valida continuidad.

    Devuelve un dict con origen/destino/km_total/precio_cliente_total, o None
    si no se pasaron rutas.
    """
    if not ruta_ids:
        return None

    rutas = _obtener_rutas_por_ids(cursor, ruta_ids)
    validar_continuidad(rutas)

    km_total = 0.0
    precio_cliente_total = 0.0
    for orden, (ruta_id, ruta) in enumerate(zip(ruta_ids, rutas), start=1):
        estado = "en_curso" if orden == 1 else "pendiente"
        cursor.execute(
            f"INSERT INTO viaje_tramos (viaje_id, ruta_id, orden, estado) "
            f"VALUES ({ph()}, {ph()}, {ph()}, {ph()})",
            (viaje_id, ruta_id, orden, estado)
        )
        km_ruta = float(ruta["km_oficiales"] or 0)
        tarifa_ruta = float(ruta["tarifa_km"] or 0)
        km_total += km_ruta
        precio_cliente_total += km_ruta * tarifa_ruta

    return {
        "origen": rutas[0]["origen"],
        "destino": rutas[-1]["destino"],
        "km_total": km_total,
        "precio_cliente_total": precio_cliente_total,
    }


def obtener_tramos_viaje(viaje_id):
    con = conectar()
    cur = con.cursor()
    cur.execute(f"""
        SELECT vt.id, vt.viaje_id, vt.ruta_id, vt.orden, vt.estado, vt.fecha_llegada,
               r.nombre AS ruta_nombre, r.origen, r.destino, r.km_oficiales, r.tarifa_km
        FROM viaje_tramos vt
        JOIN rutas r ON r.id = vt.ruta_id
        WHERE vt.viaje_id = {ph()}
        ORDER BY vt.orden ASC
    """, (viaje_id,))
    rows = cur.fetchall()
    con.close()
    return [dict(row) for row in rows]


def calcular_totales_tramos(viaje_id):
    """km total y precio cliente sumados a partir de los tramos de un viaje.
    Devuelve None si el viaje no tiene tramos (comportamiento simple)."""
    tramos = obtener_tramos_viaje(viaje_id)
    if not tramos:
        return None
    km_total = sum(float(t["km_oficiales"] or 0) for t in tramos)
    precio_cliente_total = sum(
        float(t["km_oficiales"] or 0) * float(t["tarifa_km"] or 0) for t in tramos
    )
    return {"km_total": km_total, "precio_cliente_total": precio_cliente_total}


def completar_tramo(cursor, viaje_id, tramo_id):
    """Marca como completado el tramo indicado si es el tramo activo (en_curso)
    del viaje, y activa el siguiente en orden. No permite saltar tramos.
    Usa el cursor de la transacción activa del llamador; no comitea ni abre
    conexión propia. Devuelve True si se completó, False si el tramo no
    estaba en_curso."""
    cursor.execute(
        f"SELECT id, orden, estado FROM viaje_tramos WHERE id = {ph()} AND viaje_id = {ph()}",
        (tramo_id, viaje_id)
    )
    tramo = cursor.fetchone()
    if not tramo or tramo["estado"] != "en_curso":
        return False

    cursor.execute(
        f"UPDATE viaje_tramos SET estado = 'completado', fecha_llegada = CURRENT_TIMESTAMP "
        f"WHERE id = {ph()}",
        (tramo_id,)
    )
    cursor.execute(
        f"UPDATE viaje_tramos SET estado = 'en_curso' WHERE viaje_id = {ph()} AND orden = {ph()}",
        (viaje_id, tramo["orden"] + 1)
    )
    return True


def tramos_completados(viaje_id):
    """True/False si el viaje tiene tramos y están (o no) todos completados.
    None si el viaje no usa tramos."""
    tramos = obtener_tramos_viaje(viaje_id)
    if not tramos:
        return None
    return all(t["estado"] == "completado" for t in tramos)
