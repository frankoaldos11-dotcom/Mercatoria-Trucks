from flask import Blueprint, render_template
import sqlite3

dashboard_bp = Blueprint("dashboard", __name__)


def conectar():
    return sqlite3.connect("mercatoria.db")


@dashboard_bp.route("/dashboard")
def dashboard():
    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("SELECT COUNT(*) FROM viajes")
    total_viajes = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(precio), 0) FROM viajes")
    facturacion_total = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(comision), 0) FROM viajes")
    comision_total = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(beneficio), 0) FROM viajes")
    beneficio_total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM viajes WHERE estado='Pendiente'")
    pendientes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM viajes WHERE estado='Asignado'")
    asignados = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM viajes WHERE estado='En ruta'")
    en_ruta = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM viajes WHERE estado='Entregado'")
    entregados = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM viajes WHERE estado='Cancelado'")
    cancelados = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM camioneros WHERE estado='Disponible'")
    camioneros_disponibles = cursor.fetchone()[0]

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