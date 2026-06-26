from flask import Blueprint, render_template, request, session, redirect, url_for
from database import conectar
from extensions import bcrypt

cliente_bp = Blueprint("cliente", __name__, url_prefix="/cliente")

PASOS_ESTADO = {
    "Solicitado": 0,
    "Asignado": 1,
    "Pendiente de pago": 1,
    "Confirmado": 1,
    "Carga recogida": 2,
    "En ruta": 2,
    "Entregado": 3,
    "Cancelado": -1,
}


def _requiere_cliente():
    return "usuario" in session and session.get("rol") == "cliente"


@cliente_bp.route("/login", methods=["GET", "POST"])
def login():
    if _requiere_cliente():
        return redirect(url_for("cliente.cliente_home"))

    error = None
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        con = conectar()
        cur = con.cursor()
        cur.execute(
            "SELECT id, password, rol FROM usuarios WHERE usuario = ? AND rol = 'cliente'",
            (email,)
        )
        fila = cur.fetchone()
        con.close()

        if fila and bcrypt.check_password_hash(fila["password"], password):
            session["usuario"] = email
            session["rol"] = fila["rol"]
            session["user_id"] = fila["id"]
            return redirect(url_for("cliente.cliente_home"))

        error = "Correo o contraseña incorrectos"

    registrado = request.args.get("registrado")
    return render_template("cliente/login.html", error=error, registrado=registrado)


@cliente_bp.route("/registro", methods=["GET", "POST"])
def registro():
    if _requiere_cliente():
        return redirect(url_for("cliente.cliente_home"))

    if request.method == "POST":
        nombre    = request.form["nombre"].strip()
        apellidos = request.form["apellidos"].strip()
        email     = request.form["email"].strip().lower()
        telefono  = request.form["telefono"].strip()
        empresa   = request.form.get("empresa", "").strip()
        password  = request.form["password"]
        confirmar = request.form["confirmar"]

        form = request.form

        if not nombre or not email or not password:
            return render_template("cliente/registro.html",
                                   error="Nombre, correo y contraseña son obligatorios",
                                   form=form)

        if password != confirmar:
            return render_template("cliente/registro.html",
                                   error="Las contraseñas no coinciden", form=form)

        if len(password) < 6:
            return render_template("cliente/registro.html",
                                   error="La contraseña debe tener al menos 6 caracteres",
                                   form=form)

        con = conectar()
        cur = con.cursor()
        cur.execute("SELECT id FROM usuarios WHERE usuario = ?", (email,))
        if cur.fetchone():
            con.close()
            return render_template("cliente/registro.html",
                                   error="Este correo ya está registrado", form=form)

        hash_pw = bcrypt.generate_password_hash(password).decode("utf-8")
        cur.execute("""
            INSERT INTO usuarios (usuario, password, rol, nombre, apellidos, telefono, empresa)
            VALUES (?, ?, 'cliente', ?, ?, ?, ?)
        """, (email, hash_pw, nombre, apellidos, telefono, empresa))

        usuario_id = cur.lastrowid
        nombre_completo = f"{nombre} {apellidos}".strip()
        cur.execute("""
            INSERT INTO clientes (usuario_id, nombre, contacto, telefono, email, empresa)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (usuario_id, nombre_completo, nombre, telefono, email, empresa))

        con.commit()
        con.close()
        return redirect(url_for("cliente.login") + "?registrado=1")

    return render_template("cliente/registro.html")


@cliente_bp.route("/")
def cliente_home():
    if not _requiere_cliente():
        return redirect(url_for("cliente.login"))

    con = conectar()
    cur = con.cursor()

    cur.execute("""
        SELECT id, origen, destino, estado, camionero_nombre, fecha_creacion
        FROM viajes WHERE cliente = ?
        ORDER BY id DESC LIMIT 5
    """, (session["usuario"],))
    recientes = cur.fetchall()

    cur.execute("""
        SELECT COUNT(*) FROM viajes
        WHERE cliente = ? AND estado NOT IN ('Entregado', 'Cancelado')
    """, (session["usuario"],))
    activos = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM viajes WHERE cliente = ?", (session["usuario"],))
    total = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM viajes WHERE cliente = ? AND estado = 'Entregado'
    """, (session["usuario"],))
    entregados = cur.fetchone()[0]

    cur.execute("SELECT nombre, apellidos FROM usuarios WHERE usuario = ?",
                (session["usuario"],))
    u = cur.fetchone()
    nombre = (u["nombre"] or "").strip() if u else ""
    if not nombre:
        nombre = session["usuario"].split("@")[0]

    con.close()
    return render_template("cliente/home.html",
                           recientes=recientes,
                           activos=activos,
                           total=total,
                           entregados=entregados,
                           nombre=nombre)


@cliente_bp.route("/viajes")
def mis_viajes():
    if not _requiere_cliente():
        return redirect(url_for("cliente.login"))

    filtro = request.args.get("estado", "todos")
    nuevo  = request.args.get("nuevo")

    con = conectar()
    cur = con.cursor()

    base = """
        SELECT id, origen, destino, estado, camionero_nombre, fecha_creacion
        FROM viajes WHERE cliente = ?
    """
    if filtro == "activos":
        cur.execute(base + "AND estado NOT IN ('Entregado','Cancelado') ORDER BY id DESC",
                    (session["usuario"],))
    elif filtro == "entregados":
        cur.execute(base + "AND estado = 'Entregado' ORDER BY id DESC",
                    (session["usuario"],))
    else:
        cur.execute(base + "ORDER BY id DESC", (session["usuario"],))

    viajes = cur.fetchall()
    con.close()
    return render_template("cliente/viajes.html", viajes=viajes, filtro=filtro, nuevo=nuevo)


@cliente_bp.route("/viaje/<int:viaje_id>")
def detalle_viaje(viaje_id):
    if not _requiere_cliente():
        return redirect(url_for("cliente.login"))

    con = conectar()
    cur = con.cursor()
    cur.execute("""
        SELECT v.id, v.origen, v.destino, v.estado, v.camionero_nombre,
               v.fecha_creacion, v.fecha_asignacion, v.fecha_recogida, v.fecha_entrega,
               v.observaciones,
               COALESCE(veh.marca, '') as vehiculo_marca,
               COALESCE(veh.modelo, '') as vehiculo_modelo,
               COALESCE(veh.matricula, veh.placa, '') as vehiculo_placa,
               COALESCE(r.nombre, '') as ruta_nombre,
               COALESCE(r.km_oficiales, 0) as km_ruta
        FROM viajes v
        LEFT JOIN vehiculos veh ON v.vehiculo_id = veh.id
        LEFT JOIN rutas r ON v.ruta_id = r.id
        WHERE v.id = ? AND v.cliente = ?
    """, (viaje_id, session["usuario"]))
    viaje = cur.fetchone()
    con.close()

    if not viaje:
        return redirect(url_for("cliente.mis_viajes"))

    paso_actual = PASOS_ESTADO.get(viaje["estado"], 0)
    return render_template("cliente/viaje_detalle.html", viaje=viaje, paso_actual=paso_actual)


@cliente_bp.route("/solicitar", methods=["GET", "POST"])
def solicitar_envio():
    if not _requiere_cliente():
        return redirect(url_for("cliente.login"))

    con = conectar()
    cur = con.cursor()

    if request.method == "POST":
        ruta_id = request.form.get("ruta_id", "").strip()
        tipo    = request.form.get("tipo", "").strip()
        peso    = request.form.get("peso", "").strip()
        notas   = request.form.get("notas", "").strip()

        if not ruta_id or not tipo or not peso:
            cur.execute("SELECT id, nombre, origen, destino FROM rutas WHERE activa = 1 ORDER BY nombre",)
            rutas = cur.fetchall()
            con.close()
            return render_template("cliente/solicitar.html", rutas=rutas,
                                   error="Selecciona la ruta, tipo de carga y peso aproximado")

        cur.execute("SELECT origen, destino FROM rutas WHERE id = ?", (ruta_id,))
        ruta = cur.fetchone()
        origen  = ruta["origen"]  if ruta else ""
        destino = ruta["destino"] if ruta else ""

        cur.execute("SELECT id FROM clientes WHERE usuario_id = ?", (session["user_id"],))
        cliente_row = cur.fetchone()
        cliente_id = cliente_row["id"] if cliente_row else None

        obs = f"Tipo de carga: {tipo} | Peso aprox.: {peso}"
        if notas:
            obs += f"\nNotas: {notas}"

        cur.execute("""
            INSERT INTO viajes (cliente, cliente_id, ruta_id, origen, destino, precio, combustible,
                                camionero, comision, beneficio, estado, observaciones)
            VALUES (?, ?, ?, ?, ?, 0, 0, '', 0, 0, 'Solicitado', ?)
        """, (session["usuario"], cliente_id, ruta_id, origen, destino, obs))
        con.commit()
        con.close()
        return redirect(url_for("cliente.mis_viajes", nuevo=1))

    cur.execute("SELECT id, nombre, origen, destino FROM rutas WHERE activa = 1 ORDER BY nombre")
    rutas = cur.fetchall()
    con.close()
    return render_template("cliente/solicitar.html", rutas=rutas)


@cliente_bp.route("/perfil", methods=["GET", "POST"])
def perfil():
    if not _requiere_cliente():
        return redirect(url_for("cliente.login"))

    con = conectar()
    cur = con.cursor()
    cur.execute("""
        SELECT nombre, apellidos, telefono, empresa, usuario, password
        FROM usuarios WHERE usuario = ?
    """, (session["usuario"],))
    datos = cur.fetchone()

    if request.method == "POST":
        nombre    = request.form["nombre"].strip()
        apellidos = request.form.get("apellidos", "").strip()
        telefono  = request.form.get("telefono", "").strip()
        empresa   = request.form.get("empresa", "").strip()
        actual    = request.form.get("actual", "").strip()
        nueva     = request.form.get("nueva", "").strip()
        confirmar = request.form.get("confirmar_pw", "").strip()

        if not nombre:
            con.close()
            return render_template("cliente/perfil.html", datos=datos,
                                   error="El nombre no puede estar vacío")

        cur.execute("""
            UPDATE usuarios SET nombre = ?, apellidos = ?, telefono = ?, empresa = ?
            WHERE usuario = ?
        """, (nombre, apellidos, telefono, empresa, session["usuario"]))
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
            if len(nueva) < 6:
                con.close()
                return render_template("cliente/perfil.html", datos=datos,
                                       error="La nueva contraseña debe tener al menos 6 caracteres")
            nuevo_hash = bcrypt.generate_password_hash(nueva).decode("utf-8")
            cur.execute("UPDATE usuarios SET password = ? WHERE usuario = ?",
                        (nuevo_hash, session["usuario"]))
            con.commit()

        cur.execute("""
            SELECT nombre, apellidos, telefono, empresa, usuario, password
            FROM usuarios WHERE usuario = ?
        """, (session["usuario"],))
        datos = cur.fetchone()
        con.close()
        return render_template("cliente/perfil.html", datos=datos,
                               mensaje="Datos actualizados correctamente")

    con.close()
    return render_template("cliente/perfil.html", datos=datos)


@cliente_bp.route("/activos")
def activos():
    return redirect(url_for("cliente.mis_viajes", estado="activos"))


@cliente_bp.route("/historico")
def historico():
    return redirect(url_for("cliente.mis_viajes", estado="entregados"))
