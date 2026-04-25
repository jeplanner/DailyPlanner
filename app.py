import os
from flask import Flask, session, request, jsonify, render_template, send_from_directory
from flask_login import current_user
from werkzeug.middleware.proxy_fix import ProxyFix
from logger import setup_logger
from settings import config_map
from extensions import login_manager, csrf, limiter

logger = setup_logger()


def create_app():
    app = Flask(__name__)

    # ── Config ──────────────────────────────────────────
    env = os.environ.get("FLASK_ENV", "production")
    app.config.from_object(config_map.get(env, config_map["production"]))

    # Static files (CSS, JS, deity portraits, icons) get a 30-day
    # browser-cache so phones don't re-download them on every visit.
    # We cache-bust by adding ?v=<deploy id> to URLs that change; static
    # assets here are content-stable so a long max-age is safe and
    # dramatically reduces /prayer's bandwidth bill on repeat visits.
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 60 * 60 * 24 * 30  # 30 days

    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1
    )

    # ── Extensions ──────────────────────────────────────
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from models.user import User
        return User.get(user_id)

    # ── Session bridge ──────────────────────────────────
    # Keeps session["user_id"] populated for all existing routes
    @app.before_request
    def sync_session_user_id():
        if current_user.is_authenticated:
            session["user_id"] = current_user.get_id()
            session["authenticated"] = True

    # ── Security headers ────────────────────────────────
    from middleware.security import apply_security_headers
    apply_security_headers(app)

    # ── Blueprints ──────────────────────────────────────
    from routes.auth import auth_bp
    from routes.planner import planner_bp
    from routes.todo import todo_bp
    from routes.projects import projects_bp
    from routes.health import health_bp
    from routes.habits import habits_bp
    from routes.references import references_bp
    from routes.ai import ai_bp
    from routes.events import events_bp
    from routes.timeline import timeline_bp
    from routes.notes import notes_bp
    from routes.system import system_bp
    from routes.inbox import inbox_bp
    from routes.refcards import refcards_bp
    from routes.portfolio import portfolio_bp
    from routes.goals import goals_bp
    from routes.reports import reports_bp
    from routes.settings import settings_bp
    from routes.checklist import checklist_bp
    from routes.push import push_bp
    from routes.prayer import prayer_bp
    from routes.relationships import relationships_bp
    from routes.focus_log import focus_log_bp
    from routes.photos import photos_bp
    from routes.quotes import quotes_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(planner_bp)
    app.register_blueprint(todo_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(habits_bp)
    app.register_blueprint(references_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(timeline_bp)
    app.register_blueprint(notes_bp)
    app.register_blueprint(inbox_bp)
    app.register_blueprint(refcards_bp)
    app.register_blueprint(portfolio_bp)
    app.register_blueprint(goals_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(checklist_bp)
    app.register_blueprint(push_bp)
    app.register_blueprint(prayer_bp)
    app.register_blueprint(relationships_bp)
    app.register_blueprint(focus_log_bp)
    app.register_blueprint(photos_bp)
    app.register_blueprint(quotes_bp)

    # ── Exempt JSON API blueprints from CSRF ────────────
    # These use session auth + @login_required, not form tokens
    csrf.exempt(events_bp)
    csrf.exempt(habits_bp)
    csrf.exempt(health_bp)
    csrf.exempt(ai_bp)
    csrf.exempt(inbox_bp)
    csrf.exempt(timeline_bp)
    csrf.exempt(projects_bp)
    csrf.exempt(todo_bp)
    csrf.exempt(planner_bp)
    csrf.exempt(notes_bp)
    csrf.exempt(refcards_bp)
    csrf.exempt(portfolio_bp)
    csrf.exempt(references_bp)
    csrf.exempt(goals_bp)
    csrf.exempt(reports_bp)
    csrf.exempt(settings_bp)
    csrf.exempt(checklist_bp)
    csrf.exempt(push_bp)
    csrf.exempt(focus_log_bp)
    csrf.exempt(prayer_bp)
    csrf.exempt(photos_bp)

    # ── PWA: serve SW + manifest from the site root so the service
    # worker's scope is "/" (otherwise it's confined to /static/...).
    @app.route("/service-worker.js")
    def _service_worker():
        return send_from_directory(
            app.static_folder, "service-worker.js",
            mimetype="application/javascript",
        )

    @app.route("/manifest.json")
    def _manifest():
        return send_from_directory(
            app.static_folder, "manifest.json",
            mimetype="application/manifest+json",
        )

    # ── Start the push reminder scheduler (idempotent) ──
    try:
        from services import push_scheduler
        push_scheduler.start(app)
    except Exception:
        logger.exception("Could not start push scheduler")

    # ── OAuth dev override ──────────────────────────────
    if env == "development":
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    # ── Error handlers ──────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"status": "error", "error": "Not found"}), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(429)
    def rate_limited(e):
        from flask_limiter.util import get_remote_address
        logger.warning("Rate limit exceeded for IP=%s path=%s",
                       get_remote_address(), request.path)
        return jsonify({"status": "error", "error": "Too many requests. Please slow down."}), 429

    @app.errorhandler(500)
    def server_error(e):
        logger.exception("Unhandled server error")
        if request.path.startswith("/api/"):
            return jsonify({"status": "error", "error": "Internal server error"}), 500
        return render_template("errors/500.html"), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        # logger.exception captures the traceback through the logger,
        # avoiding stack-trace leakage to stdout in production.
        logger.exception("Unhandled exception: %s", str(e))
        if request.path.startswith("/api/"):
            return jsonify({"status": "error", "error": "Internal server error"}), 500
        raise e

    return app
