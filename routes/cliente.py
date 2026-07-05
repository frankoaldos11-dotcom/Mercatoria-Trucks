import io
import secrets
import threading
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, session, redirect, url_for, current_app, send_file
from flask_mail import Message
from database import conectar, crear_checklist_viaje
from extensions import bcrypt, mail
from services.tramos_service import (
    ContinuidadError, crear_tramos_viaje, obtener_tramos_viaje, validar_continuidad,
)


def enviar_bienvenida(app, email, nombre):
    with app.app_context():
        try:
            from flask_mail import Message
            from extensions import mail
            msg = Message(
                subject="Bienvenido a Mercatoria Truck",
                recipients=[email]
            )
            msg.body = f"""Hola {nombre},

Tu cuenta en Mercatoria Truck ha sido creada exitosamente.

Accede a tu portal en:
https://mercatoria-trucks.onrender.com/cliente

— Mercatoria Truck
"""
            mail.send(msg)
        except Exception as e:
            app.logger.error(f"Error enviando email bienvenida a {email}: {e}")

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

    if request.method == "GET":
        return redirect("/login")

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

        if fila and bcrypt.check_password_hash(fila["password"], password):
            cur.execute("SELECT nombre, apellidos FROM usuarios WHERE id = ?", (fila["id"],))
            u = cur.fetchone()
            nombre = ""
            if u:
                nombre = f"{u['nombre'] or ''} {u['apellidos'] or ''}".strip()
            if not nombre:
                nombre = email.split("@")[0]
            session["nombre"] = nombre
            con.close()
            session.permanent = True
            session["usuario"] = email
            session["rol"] = fila["rol"]
            session["user_id"] = fila["id"]
            return redirect(url_for("cliente.cliente_home"))

        con.close()

        error = "Correo o contraseña incorrectos"

    registrado = request.args.get("registrado")
    reset = request.args.get("reset")
    return render_template("cliente/login.html", error=error, registrado=registrado, reset=reset)


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

        t = threading.Thread(target=enviar_bienvenida, args=(current_app._get_current_object(), email, nombre))
        t.daemon = True
        t.start()

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
        SELECT COUNT(*) AS total FROM viajes
        WHERE cliente = ? AND estado NOT IN ('Entregado', 'Cancelado')
    """, (session["usuario"],))
    activos = cur.fetchone()["total"]

    cur.execute("SELECT COUNT(*) AS total FROM viajes WHERE cliente = ?", (session["usuario"],))
    total = cur.fetchone()["total"]

    cur.execute("""
        SELECT COUNT(*) AS total FROM viajes WHERE cliente = ? AND estado = 'Entregado'
    """, (session["usuario"],))
    entregados = cur.fetchone()["total"]

    cur.execute("SELECT nombre, apellidos FROM usuarios WHERE usuario = ?",
                (session["usuario"],))
    u = cur.fetchone()
    nombre = (u["nombre"] or "").strip() if u else ""
    if not nombre:
        nombre = session["usuario"].split("@")[0]

    cur.execute("""
        SELECT COALESCE(categoria, 'Normal') AS categoria
        FROM clientes WHERE usuario_id = (SELECT id FROM usuarios WHERE usuario = ?)
    """, (session["usuario"],))
    cl = cur.fetchone()
    categoria_cliente = cl["categoria"] if cl else "Normal"

    con.close()
    return render_template("cliente/home.html",
                           recientes=recientes,
                           activos=activos,
                           total=total,
                           entregados=entregados,
                           nombre=nombre,
                           categoria_cliente=categoria_cliente)


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

    cur.execute(
        "SELECT id FROM clientes WHERE usuario_id = ?",
        (session["user_id"],)
    )
    cliente_row = cur.fetchone()
    if not cliente_row:
        con.close()
        return redirect(url_for("cliente.mis_viajes"))
    cliente_id = cliente_row["id"]

    cur.execute("""
        SELECT v.id, v.origen, v.destino, v.estado, v.camionero_nombre,
               v.fecha_creacion, v.fecha_asignacion, v.fecha_recogida,
               v.fecha_entrega, v.observaciones,
               COALESCE(NULLIF(v.precio_final,0), NULLIF(v.precio_cliente,0),
                        NULLIF(v.precio,0), 0) AS precio_confirmado,
               COALESCE(veh.marca, '') AS vehiculo_marca,
               COALESCE(veh.modelo, '') AS vehiculo_modelo,
               COALESCE(veh.matricula, '') AS vehiculo_placa,
               COALESCE(r.nombre, '') AS ruta_nombre,
               COALESCE(r.km_oficiales, 0) AS km_ruta
        FROM viajes v
        LEFT JOIN vehiculos veh ON v.vehiculo_id = veh.id
        LEFT JOIN rutas r ON v.ruta_id = r.id
        WHERE v.id = ? AND (v.cliente_id = ? OR v.cliente = ?)
    """, (viaje_id, cliente_id, session.get("usuario", "")))
    viaje = cur.fetchone()
    con.close()

    if not viaje:
        return redirect(url_for("cliente.mis_viajes"))

    paso_actual = PASOS_ESTADO.get(viaje["estado"], 0)
    tramos = obtener_tramos_viaje(viaje_id)
    return render_template(
        "cliente/viaje_detalle.html",
        viaje=viaje,
        paso_actual=paso_actual,
        tramos=tramos,
        factura_error=request.args.get("factura_error")
    )


@cliente_bp.route("/viaje/<int:viaje_id>/factura")
def descargar_factura(viaje_id):
    if not _requiere_cliente():
        return redirect(url_for("cliente.login"))

    con = conectar()
    cur = con.cursor()
    cur.execute("SELECT id FROM clientes WHERE usuario_id = ?", (session["user_id"],))
    cliente_row = cur.fetchone()
    if not cliente_row:
        con.close()
        return redirect(url_for("cliente.mis_viajes"))
    cliente_id = cliente_row["id"]

    cur.execute(
        "SELECT id, estado FROM viajes WHERE id = ? AND cliente_id = ?",
        (viaje_id, cliente_id)
    )
    viaje = cur.fetchone()
    con.close()

    if not viaje:
        return redirect(url_for("cliente.mis_viajes"))

    if (viaje["estado"] or "").lower() != "entregado":
        return redirect(url_for("cliente.detalle_viaje", viaje_id=viaje_id))

    try:
        from services.pdf_service import generar_factura_cliente
        pdf_bytes = generar_factura_cliente(viaje_id)
    except ValueError as e:
        return redirect(url_for("cliente.detalle_viaje", viaje_id=viaje_id, factura_error=str(e)))
    except Exception as e:
        current_app.logger.error(f"Error generando factura viaje #{viaje_id}: {e}")
        return redirect(url_for(
            "cliente.detalle_viaje", viaje_id=viaje_id,
            factura_error="No se pudo generar la factura. Contacta con soporte si el problema persiste."
        ))

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"factura-{viaje_id:04d}.pdf",
    )


@cliente_bp.route("/solicitar", methods=["GET", "POST"])
def solicitar_envio():
    if not _requiere_cliente():
        return redirect(url_for("cliente.login"))

    con = conectar()
    cur = con.cursor()

    if request.method == "POST":
        ruta_ids           = [r.strip() for r in request.form.getlist("ruta_id") if r.strip()]
        tipo_carga         = request.form.get("tipo_carga", "").strip()
        tipo_transporte    = request.form.get("tipo_transporte", "").strip()
        peso_str           = request.form.get("peso_toneladas", "").strip()
        referencia_cliente = None
        prioridad          = "Normal"
        cantidad_str       = request.form.get("cantidad_contenedores", "").strip()
        numero_contenedor  = request.form.get("numero_contenedor", "").strip()
        notas              = request.form.get("notas", "").strip()
        obs_operativas     = request.form.get("observaciones_operativas", "").strip()

        def _err(msg):
            cur.execute("SELECT id, nombre, origen, destino FROM rutas WHERE activa = 1 ORDER BY nombre")
            rutas_err = cur.fetchall()
            con.close()
            return render_template("cliente/solicitar.html", rutas=rutas_err, error=msg)

        if not ruta_ids or not tipo_carga:
            return _err("Selecciona la ruta y el tipo de carga")

        if not peso_str:
            return _err("Indica el peso en toneladas")

        try:
            peso_toneladas = float(peso_str)
        except ValueError:
            return _err("El peso debe ser un número válido (Ej: 2.5)")

        cantidad_contenedores = None
        if cantidad_str:
            try:
                cantidad_contenedores = int(cantidad_str)
            except ValueError:
                pass

        try:
            ruta_ids = [int(r) for r in ruta_ids]
        except ValueError:
            return _err("La ruta seleccionada no es válida. Por favor elige una de la lista.")

        placeholders = ",".join("?" for _ in ruta_ids)
        cur.execute(
            f"SELECT id, origen, destino FROM rutas WHERE id IN ({placeholders}) AND activa = 1",
            ruta_ids
        )
        rutas_por_id = {r["id"]: r for r in cur.fetchall()}
        if len(rutas_por_id) != len(set(ruta_ids)):
            return _err("La ruta seleccionada no es válida. Por favor elige una de la lista.")
        rutas_ordenadas = [rutas_por_id[rid] for rid in ruta_ids]

        try:
            validar_continuidad(rutas_ordenadas)
        except ContinuidadError as e:
            return _err(str(e))

        ruta_id = ruta_ids[0]
        origen  = rutas_ordenadas[0]["origen"]
        destino = rutas_ordenadas[-1]["destino"]

        cur.execute("SELECT id FROM clientes WHERE usuario_id = ?", (session["user_id"],))
        cliente_row = cur.fetchone()
        if cliente_row:
            cliente_id = cliente_row["id"]
        else:
            email_usuario = session.get("usuario", "")
            nombre_fallback = session.get("nombre") or email_usuario.split("@")[0] or "Cliente"
            cur.execute("""
                INSERT INTO clientes (usuario_id, nombre, email, contacto, telefono)
                VALUES (?, ?, ?, ?, ?)
            """, (session["user_id"], nombre_fallback, email_usuario, email_usuario, ""))
            cliente_id = cur.lastrowid
            con.commit()

        cur.execute("""
            INSERT INTO viajes (
                cliente, cliente_id, ruta_id, origen, destino,
                precio, combustible, comision, beneficio, estado,
                observaciones, referencia_cliente, prioridad,
                tipo_carga, tipo_transporte, cantidad_contenedores,
                numero_contenedor, peso_toneladas, observaciones_operativas
            )
            VALUES (?, ?, ?, ?, ?, 0, 0, 0, 0, 'Solicitado',
                    ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session["usuario"], cliente_id, ruta_id, origen, destino,
            notas or None,
            referencia_cliente or None,
            prioridad,
            tipo_carga,
            tipo_transporte or None,
            cantidad_contenedores,
            numero_contenedor or None,
            peso_toneladas,
            obs_operativas or None,
        ))
        viaje_id = cur.lastrowid
        crear_checklist_viaje(cur, viaje_id)
        if len(ruta_ids) > 1:
            crear_tramos_viaje(cur, viaje_id, ruta_ids)
        con.commit()
        con.close()
        return redirect(url_for("cliente.mis_viajes", nuevo=1))

    cur.execute("SELECT id, nombre, origen, destino FROM rutas WHERE activa = 1 ORDER BY nombre")
    rutas = cur.fetchall()
    con.close()
    return render_template("cliente/solicitar.html", rutas=rutas)


@cliente_bp.route("/viaje/<int:viaje_id>/cancelar", methods=["POST"])
def cancelar_viaje(viaje_id):
    if not _requiere_cliente():
        return redirect(url_for("cliente.login"))
    con = conectar()
    cur = con.cursor()
    cur.execute(
        "SELECT id, estado FROM viajes WHERE id = ? AND cliente = ?",
        (viaje_id, session["usuario"])
    )
    viaje = cur.fetchone()
    if viaje and viaje["estado"].lower() == "solicitado":
        cur.execute(
            "UPDATE viajes SET estado = 'Cancelado' WHERE id = ?",
            (viaje_id,)
        )
        con.commit()
    con.close()
    return redirect(url_for("cliente.detalle_viaje", viaje_id=viaje_id))


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

    cur.execute("""
        SELECT
            COALESCE(SUM(
                CASE WHEN LOWER(v.estado) = 'entregado'
                THEN COALESCE(r.km_oficiales, v.km, v.kilometros, 0)
                ELSE 0 END
            ), 0) AS km_recorridos,
            COALESCE(SUM(COALESCE(v.peso_toneladas, 0)), 0) AS toneladas
        FROM viajes v
        LEFT JOIN rutas r ON v.ruta_id = r.id
        WHERE v.cliente = ?
    """, (session["usuario"],))
    _m = cur.fetchone()
    km_recorridos = int(_m["km_recorridos"]) if _m else 0
    toneladas = float(_m["toneladas"]) if _m else 0.0

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
                                   km_recorridos=km_recorridos, toneladas=toneladas,
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
                                       km_recorridos=km_recorridos, toneladas=toneladas,
                                       error="La contraseña actual es incorrecta")
            if nueva != confirmar:
                con.close()
                return render_template("cliente/perfil.html", datos=datos,
                                       km_recorridos=km_recorridos, toneladas=toneladas,
                                       error="Las contraseñas nuevas no coinciden")
            if len(nueva) < 6:
                con.close()
                return render_template("cliente/perfil.html", datos=datos,
                                       km_recorridos=km_recorridos, toneladas=toneladas,
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
                               km_recorridos=km_recorridos, toneladas=toneladas,
                               mensaje="Datos actualizados correctamente")

    con.close()
    return render_template("cliente/perfil.html", datos=datos,
                           km_recorridos=km_recorridos, toneladas=toneladas)


@cliente_bp.route("/recuperar", methods=["GET", "POST"])
def recuperar_password():
    if request.method == "GET":
        return render_template("cliente/recuperar.html")

    email = request.form.get("email", "").strip().lower()
    if not email:
        return render_template("cliente/recuperar.html",
                               error="Ingresa tu correo electrónico")

    con = conectar()
    cur = con.cursor()
    cur.execute("SELECT id, nombre FROM usuarios WHERE usuario = ? AND rol = 'cliente'", (email,))
    usuario = cur.fetchone()

    if usuario:
        token = secrets.token_urlsafe(32)
        expira = (datetime.utcnow() + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            "INSERT INTO reset_tokens (token, usuario, expira) VALUES (?, ?, ?)",
            (token, email, expira)
        )
        con.commit()
        nombre = usuario["nombre"] or email.split("@")[0]
        try:
            msg = Message(
                subject="Recuperación de contraseña — Mercatoria Truck",
                recipients=[email]
            )
            msg.body = f"""Hola {nombre},

Recibimos una solicitud para restablecer tu contraseña en Mercatoria Truck.

Haz clic en el siguiente enlace (válido por 30 minutos):
https://mercatoria-trucks.onrender.com/cliente/reset/{token}

Si no solicitaste este cambio, ignora este mensaje.

— Mercatoria Truck
"""
            mail.send(msg)
        except Exception as e:
            current_app.logger.error(f"Error enviando email recuperacion a {email}: {e}")

    con.close()
    return render_template("cliente/recuperar.html",
                           enviado=True)


@cliente_bp.route("/reset/<token>", methods=["GET", "POST"])
def reset_password(token):
    con = conectar()
    cur = con.cursor()
    cur.execute(
        "SELECT usuario, expira, usado FROM reset_tokens WHERE token = ?", (token,)
    )
    fila = cur.fetchone()

    if not fila or fila["usado"]:
        con.close()
        return render_template("cliente/reset_password.html",
                               error="El enlace no es válido o ya fue usado.", token=None)

    expira = datetime.strptime(fila["expira"], "%Y-%m-%d %H:%M:%S")
    if datetime.utcnow() > expira:
        con.close()
        return render_template("cliente/reset_password.html",
                               error="El enlace ha expirado. Solicita uno nuevo.", token=None)

    if request.method == "GET":
        con.close()
        return render_template("cliente/reset_password.html", token=token)

    nueva = request.form.get("password", "")
    confirmar = request.form.get("confirmar", "")

    if len(nueva) < 6:
        con.close()
        return render_template("cliente/reset_password.html", token=token,
                               error="La contraseña debe tener al menos 6 caracteres")
    if nueva != confirmar:
        con.close()
        return render_template("cliente/reset_password.html", token=token,
                               error="Las contraseñas no coinciden")

    nuevo_hash = bcrypt.generate_password_hash(nueva).decode("utf-8")
    cur.execute("UPDATE usuarios SET password = ? WHERE usuario = ?",
                (nuevo_hash, fila["usuario"]))
    cur.execute("UPDATE reset_tokens SET usado = 1 WHERE token = ?", (token,))
    con.commit()
    con.close()

    return redirect(url_for("cliente.login") + "?reset=1")


@cliente_bp.route("/activos")
def activos():
    return redirect(url_for("cliente.mis_viajes", estado="activos"))


@cliente_bp.route("/historico")
def historico():
    return redirect(url_for("cliente.mis_viajes", estado="entregados"))
