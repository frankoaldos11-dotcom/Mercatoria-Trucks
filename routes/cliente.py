from flask import Blueprint, render_template, request, session, redirect
from database import conectar
from extensions import bcrypt

cliente_bp = Blueprint("cliente", __name__, url_prefix="/cliente")


def requiere_cliente():
    return "usuario" in session and session.get("rol") == "cliente"


@cliente_bp.route("/")
def cliente_home():
    if not requiere_cliente():
        return redirect("/login")

    con = conectar()
    cur = con.cursor()
    cur.execute("""
        SELECT id, origen, destino, estado
        FROM viajes
        WHERE cliente = ?
        ORDER BY id DESC
        LIMIT 5
    """, (session["usuario"],))
    viajes = cur.fetchall()
    con.close()

    return render_template("cliente/home.html", viajes=viajes)


@cliente_bp.route("/solicitar", methods=["GET", "POST"])
def solicitar_envio():
    if not requiere_cliente():
        return redirect("/login")

    if request.method == "POST":
        origen  = request.form["origen"].strip()
        destino = request.form["destino"].strip()
        tipo    = request.form["tipo"].strip()
        peso    = request.form["peso"].strip()
        notas   = request.form["notas"].strip()

        if not origen or not destino or not tipo or not peso:
            return render_template("cliente/solicitar.html",
                                   error="Todos los campos obligatorios deben estar llenos")

        con = conectar()
        cur = con.cursor()
        cur.execute("""
            INSERT INTO viajes (cliente, origen, destino, precio, combustible,
                                camionero, comision, beneficio, estado, observaciones)
            VALUES (?, ?, ?, 0, 0, '', 0, 0, 'Pendiente', ?)
        """, (session["usuario"], origen, destino, notas))
        con.commit()
        con.close()

        return redirect("/cliente")

    return render_template("cliente/solicitar.html")


@cliente_bp.route("/activos")
def activos():
    if not requiere_cliente():
        return redirect("/login")

    con = conectar()
    cur = con.cursor()
    cur.execute("""
        SELECT id, origen, destino, estado, camionero_nombre
        FROM viajes
        WHERE cliente = ? AND estado != 'Entregado'
        ORDER BY id DESC
    """, (session["usuario"],))
    viajes = cur.fetchall()
    con.close()

    return render_template("cliente/activos.html", viajes=viajes)


@cliente_bp.route("/historico")
def historico():
    if not requiere_cliente():
        return redirect("/login")

    con = conectar()
    cur = con.cursor()
    cur.execute("""
        SELECT id, origen, destino, estado, camionero_nombre
        FROM viajes
        WHERE cliente = ? AND estado = 'Entregado'
        ORDER BY id DESC
    """, (session["usuario"],))
    viajes = cur.fetchall()
    con.close()

    return render_template("cliente/historico.html", viajes=viajes)


@cliente_bp.route("/perfil", methods=["GET", "POST"])
def perfil():
    if not requiere_cliente():
        return redirect("/login")

    con = conectar()
    cur = con.cursor()
    cur.execute("SELECT nombre, telefono, usuario, password FROM usuarios WHERE usuario = ?",
                (session["usuario"],))
    datos = cur.fetchone()

    if request.method == "POST":
        nombre   = request.form["nombre"].strip()
        telefono = request.form["telefono"].strip()
        actual   = request.form["actual"].strip()
        nueva    = request.form["nueva"].strip()
        confirmar = request.form["confirmar"].strip()

        if not nombre or not telefono:
            con.close()
            return render_template("cliente/perfil.html", datos=datos,
                                   error="Nombre y teléfono no pueden estar vacíos")

        cur.execute("UPDATE usuarios SET nombre = ?, telefono = ? WHERE usuario = ?",
                    (nombre, telefono, session["usuario"]))
        con.commit()

        if actual or nueva or confirmar:
            if not bcrypt.check_password_hash(datos["password"], actual):
                con.close()
                return render_template("cliente/perfil.html", datos=datos,
                                       error="La contraseña actual es incorrecta")

            if nueva != confirmar:
                con.close()
                return render_template("cliente/perfil.html", datos=datos,
                                       error="Las contraseñas nuevas no coinciden")

            nuevo_hash = bcrypt.generate_password_hash(nueva).decode("utf-8")
            cur.execute("UPDATE usuarios SET password = ? WHERE usuario = ?",
                        (nuevo_hash, session["usuario"]))
            con.commit()

        con.close()
        return render_template("cliente/perfil.html", datos=datos,
                               mensaje="Datos actualizados correctamente")

    con.close()
    return render_template("cliente/perfil.html", datos=datos)