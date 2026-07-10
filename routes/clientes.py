from flask import Blueprint, redirect
from database import conectar

clientes_bp = Blueprint("clientes", __name__)


@clientes_bp.route("/clientes", methods=["GET", "POST"])
def clientes():
    return redirect("/admin/clientes")


def get_all_clientes():
    con = conectar()
    cur = con.cursor()
    cur.execute("SELECT id, nombre FROM clientes ORDER BY nombre")
    rows = cur.fetchall()
    con.close()
    return rows
