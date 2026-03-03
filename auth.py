from flask import session, redirect, url_for
from functools import wraps

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("planner.login"))
        return fn(*args, **kwargs)
    return wrapper