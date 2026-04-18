import os
from datetime import timedelta


# Insecure development default — only used when FLASK_ENV != "production".
# ProductionConfig enforces a real secret in __init__ so a missing env var
# fails fast on boot instead of silently signing sessions with a known key.
_DEV_SECRET_FALLBACK = "dev-only-not-for-production"


class BaseConfig:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", _DEV_SECRET_FALLBACK)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_NAME = "dp_session"
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
    WTF_CSRF_TIME_LIMIT = 3600


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    RATELIMIT_ENABLED = False


class ProductionConfig(BaseConfig):
    DEBUG = False

    def __init__(self):
        secret = os.environ.get("FLASK_SECRET_KEY")
        if not secret or secret == _DEV_SECRET_FALLBACK:
            raise RuntimeError(
                "FLASK_SECRET_KEY must be set to a strong random value in production. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(48))'"
            )
        self.SECRET_KEY = secret


class TestingConfig(BaseConfig):
    TESTING = True
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False


# `from_object(...)` accepts a class OR an instance; instantiating Production
# triggers the secret check at boot.
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig(),
    "testing": TestingConfig,
}
