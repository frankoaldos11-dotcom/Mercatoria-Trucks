from flask import Blueprint, redirect, session
import sqlite3

clientes_bp = Blueprint("clientes", __name__)


def conectar():
    return sqlite3.connect("mercatoria.db")


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
