"""
conftest — shared test fixtures.

These tests are designed to run WITHOUT a live Supabase. We seed the env
with dummy creds and patch out every network call via monkeypatch so the
import chain, blueprint registration, and Jinja rendering can be
exercised on their own merits.

Run with:  python -m pytest tests/ -v
"""
import os
import sys
from unittest.mock import MagicMock

# Seed env BEFORE anything imports supabase_client / encryption utils
os.environ.setdefault("SUPABASE_URL", "http://localhost/dummy")
os.environ.setdefault("SUPABASE_KEY", "dummy-test-key")
os.environ.setdefault("FLASK_SECRET_KEY", "dummy-test-secret-key-for-pytest")
os.environ.setdefault("ENCRYPTION_KEY", "dummy-passphrase-for-tests")

# Ensure the project root is on sys.path FIRST, ahead of any parent-dir
# collisions (e.g. a stray app.py at /mnt/.../GitHub/ above this project).
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARENT = os.path.dirname(ROOT)

# Prune any sibling path that might shadow us
sys.path[:] = [p for p in sys.path if os.path.abspath(p) != PARENT]
if ROOT in sys.path:
    sys.path.remove(ROOT)
sys.path.insert(0, ROOT)

# Nuke any already-cached wrong `app`/`supabase_client` modules pytest
# may have imported via the parent's stray app.py during collection.
for mod in list(sys.modules):
    if mod == "app" or mod.startswith("app."):
        mod_file = getattr(sys.modules[mod], "__file__", "") or ""
        if mod_file and not mod_file.startswith(ROOT):
            del sys.modules[mod]

import pytest


@pytest.fixture(autouse=True)
def _stub_supabase(monkeypatch):
    """Replace every network-bound Supabase call with an in-memory stub
    that returns empty lists / pass-throughs. Guarantees tests never make
    real HTTP requests."""
    import supabase_client
    monkeypatch.setattr(supabase_client, "get", lambda *a, **kw: [])
    monkeypatch.setattr(supabase_client, "post", lambda *a, **kw: [])
    monkeypatch.setattr(supabase_client, "update", lambda *a, **kw: None)
    monkeypatch.setattr(supabase_client, "delete", lambda *a, **kw: None)
    yield


@pytest.fixture
def app():
    """Build the Flask app once per test, with CSRF disabled for simpler
    endpoint exercises.

    Uses importlib to load app.py by explicit file path, bypassing any
    parent-dir shadowing (e.g. an orphan /mnt/.../GitHub/app.py)."""
    import importlib.util
    app_path = os.path.join(ROOT, "app.py")
    spec = importlib.util.spec_from_file_location("app_project_root", app_path)
    app_mod = importlib.util.module_from_spec(spec)
    # Ensure any `app_mod.create_app()` relative imports find our modules
    sys.modules["app_project_root"] = app_mod
    spec.loader.exec_module(app_mod)
    a = app_mod.create_app()
    a.config["TESTING"] = True
    a.config["WTF_CSRF_ENABLED"] = False
    return a


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client, app):
    """A test client with an authenticated session.

    The app uses flask-login for `@login_required`, which checks
    `current_user.is_authenticated` via a `_user_id` session key + a
    registered user loader. We satisfy both here:
      1. Seed the session with both `user_id` (used by the app's own
         `session["user_id"]` reads) AND `_user_id` (flask-login's key).
      2. Register a loader that returns a minimal authenticated user.
    """
    from flask_login import UserMixin, LoginManager

    class _TestUser(UserMixin):
        id = "test-user-id"
        def get_id(self):
            return "test-user-id"

    # Make sure a login_manager exists; install a loader that returns our stub
    lm = app.extensions.get("login_manager")
    if lm is None:
        lm = LoginManager()
        lm.init_app(app)
    lm.user_loader(lambda _uid: _TestUser())

    with client.session_transaction() as sess:
        sess["user_id"] = "test-user-id"
        sess["authenticated"] = True
        sess["_user_id"] = "test-user-id"          # flask-login's key
        sess["_fresh"] = True
    return client
