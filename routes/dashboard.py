from flask import Blueprint, render_template
from database import conectar

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
def dashboard():
    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT
            COUNT(*)                                         AS total_viajes,
            COALESCE(SUM(precio),    0)                     AS facturacion_total,
            COALESCE(SUM(comision),  0)                     AS comision_total,
            COALESCE(SUM(beneficio), 0)                     AS beneficio_total,
            COUNT(CASE WHEN estado = 'Pendiente'  THEN 1 END) AS pendientes,
            COUNT(CASE WHEN estado = 'Asignado'   THEN 1 END) AS asignados,
            COUNT(CASE WHEN estado = 'En ruta'    THEN 1 END) AS en_ruta,
            COUNT(CASE WHEN estado = 'Entregado'  THEN 1 END) AS entregados,
            COUNT(CASE WHEN estado = 'Cancelado'  THEN 1 END) AS cancelados
        FROM viajes
    """)
    _stats = cursor.fetchone()
    total_viajes      = _stats["total_viajes"]
    facturacion_total = _stats["facturacion_total"]
    comision_total    = _stats["comision_total"]
    beneficio_total   = _stats["beneficio_total"]
    pendientes        = _stats["pendientes"]
    asignados         = _stats["asignados"]
    en_ruta           = _stats["en_ruta"]
    entregados        = _stats["entregados"]
    cancelados        = _stats["cancelados"]

    cursor.execute("SELECT COUNT(*) AS total FROM camioneros WHERE estado='Disponible'")
    camioneros_disponibles = cursor.fetchone()["total"]

    cursor.execute("""
    SELECT id, cliente, origen, destino, precio, comision, beneficio, estado, camionero_nombre
    FROM viajes
    ORDER BY id DESC
    LIMIT 10
    """)
    ultimos_viajes = cursor.fetchall()

    conexion.close()

    return render_template(
        "dashboard.html",
        total_viajes=total_viajes,
        facturacion_total=facturacion_total,
        comision_total=comision_total,
        beneficio_total=beneficio_total,
        pendientes=pendientes,
        asignados=asignados,
        en_ruta=en_ruta,
        entregados=entregados,
        cancelados=cancelados,
        camioneros_disponibles=camioneros_disponibles,
        ultimos_viajes=ultimos_viajes
    )
