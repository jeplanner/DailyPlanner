import re
from datetime import datetime
from flask import jsonify
import bleach


def sanitize_text(text, max_length=500):
    if not text:
        return ""
    cleaned = bleach.clean(str(text), tags=[], strip=True)
    return cleaned[:max_length]


def validate_email(email):
    if not email:
        return False
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


def validate_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def validate_uuid(uuid_str):
    if not uuid_str:
        return False
    return bool(re.match(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        str(uuid_str).lower()
    ))


def require_json_fields(data, fields):
    if not data:
        return jsonify({"status": "error", "error": "Request body is required"}), 400
    for field in fields:
        if field not in data or data[field] is None:
            return jsonify({"status": "error", "error": f"Missing required field: {field}"}), 400
    return None
