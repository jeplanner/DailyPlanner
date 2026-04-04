from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from flask_login import login_user, logout_user, current_user
from extensions import limiter
from models.user import User
import re
import logging

logger = logging.getLogger("daily_plan")

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("planner.planner"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        if not email or not password:
            return render_template("login.html", error="Email and password are required")

        user = User.get_by_email(email)
        if user and user.check_password(password):
            login_user(user, remember=True)
            session.permanent = True
            logger.info("User logged in: %s", email)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("planner.planner"))

        return render_template("login.html", error="Invalid email or password")

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


@auth_bp.route("/logout")
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("auth.login"))
