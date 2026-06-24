from flask import Blueprint, render_template, request, redirect

cliente_bp = Blueprint("cliente", __name__, url_prefix="/cliente")

@cliente_bp.route("/")
def cliente_home():
    cliente = {"nombre": "Cliente Demo"}
    return render_template("cliente/home.html", cliente=cliente)

@cliente_bp.route("/solicitar", methods=["GET", "POST"])
def solicitar():
    rutas = [
        {"id": 1, "origen": "La Habana", "destino": "Santiago"},
        {"id": 2, "origen": "La Habana", "destino": "Holguín"},
    ]

    if request.method == "POST":
        return redirect("/cliente")

    return render_template("cliente/solicitar.html", rutas=rutas)

@cliente_bp.route("/activos")
def activos():
    viajes = [
        {"id": 1, "ruta": "Habana → Santiago", "estado": "En ruta", "entrega": "Mañana"},
    ]
    return render_template("cliente/activos.html", viajes=viajes)

@cliente_bp.route("/historico")
def historico():
    viajes = [
        {"id": 1, "ruta": "Habana → Holguín", "fecha": "2024-01-10", "valoracion": "5 ★"},
    ]
    return render_template("cliente/historico.html", viajes=viajes)
