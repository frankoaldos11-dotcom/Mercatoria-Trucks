from flask import Blueprint, redirect

camioneros_bp = Blueprint("camioneros", __name__)


@camioneros_bp.route("/camioneros", methods=["GET", "POST"])
def camioneros_legacy_redirect():
    return redirect("/transportistas", code=301)


@camioneros_bp.route("/transportistas", methods=["GET", "POST"])
def transportistas():
    return redirect("/admin/transportistas")
