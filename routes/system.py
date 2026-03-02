from flask import Blueprint
system_bp = Blueprint("system", __name__)
@system_bp.route("/ping")
def ping():
    return "OK", 200
@system_bp.route("/favicon.ico")
def favicon():
    return "", 204

