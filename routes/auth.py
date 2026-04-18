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
            # Cache the user's preferred timezone in the session so the
            # rest of the app (utils.user_tz.user_now / user_today) can
            # serve "today" in the user's wall-clock without a DB hit
            # on every request.
            if getattr(user, "timezone", None):
                session["user_tz"] = user.timezone
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

    `logout_user()` by itself is not enough, because:

    1. Login is called with `remember=True` — Flask-Login plants a
       persistent `remember_token` cookie that survives session loss.
    2. Flask-Login's internal mechanism for deleting that cookie reads
       `session['_remember'] == 'clear'` inside an after_request hook,
       but the previous version of this route called `session.clear()`
       right after `logout_user()`, which wiped that flag before the
       hook could read it. Result: the cookie never got deleted, and
       on the redirect to /login the browser silently re-authenticated
       from the surviving remember_token.

    This version:
      - preserves the `_remember = 'clear'` flag by deleting the cookies
        manually on the response, matching all attributes Flask used to
        set them (path, domain, secure, samesite);
      - nukes every known cookie this app sets (session + remember_token
        + legacy `session` if a previous deployment used Flask's default
        cookie name);
      - sets no-store cache headers so the browser can't render a stale
        authenticated page from its back-forward cache.
    """
    from flask import current_app, make_response

    logout_user()
    session.clear()

    response = make_response(redirect(url_for("auth.login")))

    # Cookie attributes must match whatever set them, or the browser
    # ignores the deletion. Pull them from app config (same source as
    # the login path uses).
    session_cookie = current_app.config.get("SESSION_COOKIE_NAME", "session")
    remember_cookie = current_app.config.get("REMEMBER_COOKIE_NAME", "remember_token")
    cookie_domain = current_app.config.get("REMEMBER_COOKIE_DOMAIN") \
                    or current_app.config.get("SESSION_COOKIE_DOMAIN")
    session_secure = current_app.config.get("SESSION_COOKIE_SECURE", True)
    samesite = current_app.config.get("SESSION_COOKIE_SAMESITE", "Lax")

    # Primary delete — matches Secure + SameSite attrs.
    response.delete_cookie(session_cookie, path="/", domain=cookie_domain,
                           secure=session_secure, samesite=samesite)
    response.delete_cookie(remember_cookie, path="/", domain=cookie_domain,
                           secure=session_secure, samesite=samesite)

    # Belt-and-braces: some proxies rewrite cookies without the Secure
    # flag, or a previous deploy used a different cookie name. Deleting
    # these extra variants is harmless if they don't exist.
    response.delete_cookie(session_cookie, path="/")
    response.delete_cookie(remember_cookie, path="/")
    response.delete_cookie("session", path="/")       # Flask default name
    response.delete_cookie("remember_token", path="/")

    # Prevent the browser from restoring the Eisenhower page from its
    # bfcache after the redirect.
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response
