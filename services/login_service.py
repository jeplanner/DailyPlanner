from functools import wraps
from flask import session, redirect, url_for
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # 🔒 Require BOTH flags
        if not session.get("authenticated") or "user_id" not in session:
            session.clear()
            return redirect(url_for("planner.login"))
        return fn(*args, **kwargs)
    return wrapper
