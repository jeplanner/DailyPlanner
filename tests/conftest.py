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

# Ensure the project root is on sys.path so `import app` works
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

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
    endpoint exercises."""
    from app import create_app
    a = create_app()
    a.config["TESTING"] = True
    a.config["WTF_CSRF_ENABLED"] = False
    return a


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """A test client with an authenticated session. Uses the session-
    transaction context manager to pre-set user_id."""
    with client.session_transaction() as sess:
        sess["user_id"] = "test-user-id"
        sess["authenticated"] = True
    return client
