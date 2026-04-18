from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from flask_login import login_user, logout_user, current_user
from extensions import limiter
from models.user import User
from urllib.parse import urlparse
import re
import logging

logger = logging.getLogger("daily_plan")

auth_bp = Blueprint("auth", __name__)


def _safe_next_url(target):
    """Return `target` only if it's a same-origin relative path, else None.

    Without this guard `?next=https://evil/` is an open redirect after login.
    """
    if not target:
        return None
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return None
    if not target.startswith("/") or target.startswith("//"):
        return None
    return target


# Per-IP limit blocks bursts; per-IP+email limit blocks distributed brute force
# against a single account from many IPs.
@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
@limiter.limit(
    "10 per 15 minutes",
    methods=["POST"],
    key_func=lambda: f"login:{(request.form.get('email') or '').strip().lower()}",
)
def login():
    if current_user.is_authenticated:
        return redirect(url_for("planner.planner"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        if not email or not password:
            return render_template("login.html", error="Email and password are required",
                                   email=email)

        user = User.get_by_email(email)
        if user and user.check_password(password):
            login_user(user, remember=True)
            session.permanent = True
            logger.info("User logged in: %s", email)
            next_page = _safe_next_url(request.args.get("next"))
            return redirect(next_page or url_for("planner.planner"))

        return render_template("login.html", error="Invalid email or password",
                               email=email)

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("3 per minute", methods=["POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("planner.planner"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        display_name = (request.form.get("display_name") or "").strip()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""

        errors = []
        if not email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            errors.append("Valid email is required")
        if not display_name or len(display_name) < 2:
            errors.append("Display name must be at least 2 characters")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters")
        if password != confirm:
            errors.append("Passwords do not match")

        if not errors:
            existing = User.get_by_email(email)
            if existing:
                errors.append("An account with this email already exists")

        if errors:
            return render_template("register.html", errors=errors,
                                   email=email, display_name=display_name)

        user = User.create(email, display_name, password)
        if user:
            flash("Account created! Please log in.", "success")
            return redirect(url_for("auth.login"))

        return render_template("register.html",
                               errors=["Registration failed. Please try again."],
                               email=email, display_name=display_name)

    return render_template("register.html")


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    """Fully sign the user out.

    `logout_user()` alone is not enough: when login is called with
    `remember=True` (which we do), Flask-Login plants a persistent
    "remember-me" cookie. After `session.clear()` the next request
    silently re-authenticates the browser from that cookie, so the
    user appears never to have logged out.

    The fix is to (1) call logout_user(), (2) clear the server-side
    session, then (3) explicitly delete *both* the session cookie and
    the remember cookie on the redirect response.
    """
    from flask import current_app, make_response

    logout_user()
    session.clear()

    response = make_response(redirect(url_for("auth.login")))

    # Session cookie name — falls back to Flask's default if config is missing.
    session_cookie = current_app.config.get("SESSION_COOKIE_NAME", "session")
    response.delete_cookie(session_cookie, path="/")

    # Flask-Login's remember cookie. Default name is "remember_token";
    # honour an override if the app ever sets one.
    remember_cookie = current_app.config.get("REMEMBER_COOKIE_NAME", "remember_token")
    response.delete_cookie(remember_cookie, path="/")

    return response
