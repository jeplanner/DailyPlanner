from flask import Flask
import os
from logger import setup_logger
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

def create_app():
    app = Flask(__name__)

    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
        x_port=1
    )

    app.secret_key = os.environ["FLASK_SECRET_KEY"]

    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    # --------------------------------
    # Register Blueprints
    # --------------------------------
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

    # --------------------------------
    # OAuth dev override (SAFE)
    # --------------------------------
    if os.environ.get("FLASK_ENV") == "development":
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    @app.errorhandler(Exception)
    def handle_exception(e):
        import traceback
        print("🔥 UNHANDLED EXCEPTION")
        traceback.print_exc()
        raise e
    return app

   



















# ENTR
# Y POINT
# ==========================================================
#if __name__ == "__main__":
 #   logger.info("Starting Daily Planner – stable + Eisenhower")
    #app.run(debug=True)
