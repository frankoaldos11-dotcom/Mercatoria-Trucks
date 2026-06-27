from flask import Blueprint, redirect

camioneros_bp = Blueprint("camioneros", __name__)


@camioneros_bp.route("/camioneros", methods=["GET", "POST"])
def camioneros():
    return redirect("/admin/camioneros")
