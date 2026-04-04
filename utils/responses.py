from flask import jsonify


def api_success(data=None, message="ok", status=200):
    body = {"status": "ok"}
    if message != "ok":
        body["message"] = message
    if data is not None:
        body["data"] = data
    return jsonify(body), status


def api_error(message, status=400, details=None):
    body = {"status": "error", "error": message}
    if details:
        body["details"] = details
    return jsonify(body), status
