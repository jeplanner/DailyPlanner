"""Interview Prep (and Java, SQL, AI SDE) is visible only to listed users."""
import pytest

PAGES = ["/interview-prep", "/interview-prep/thoughts", "/ai-sde", "/ai-sde/thoughts", "/java", "/sql"]
APIS = ["/api/prep/thoughts"]


def _as(app, email):
    from flask_login import UserMixin
    class U(UserMixin):
        id = "test-user-id"
        def get_id(self):
            return "test-user-id"
    U.email = email
    lm = getattr(app, "login_manager", None) or app.extensions.get("login_manager")
    lm.user_loader(lambda _uid: U())


@pytest.mark.parametrize("email", ["venghatesh@gmail.com", "VenghateshShreya@gmail.com"])
def test_listed_users_see_prep(auth_client, app, email, monkeypatch):
    monkeypatch.delenv("PREP_USER_EMAILS", raising=False)
    _as(app, email)
    for path in PAGES:
        assert auth_client.get(path).status_code == 200, path
    html = auth_client.get("/interview-prep").get_data(as_text=True)
    assert 'href="/ai-sde"' in html and 'href="/java"' in html


def test_other_users_get_404_and_no_nav(auth_client, app, monkeypatch):
    monkeypatch.delenv("PREP_USER_EMAILS", raising=False)
    _as(app, "someone.else@gmail.com")
    for path in PAGES + APIS:
        assert auth_client.get(path).status_code == 404, path
    assert auth_client.post("/api/prep/thoughts", json={"question": "x"}).status_code == 404
    from flask import render_template_string
    with app.test_request_context("/"):
        from utils.prep_access import prep_allowed
        assert prep_allowed() is False


def test_signed_out_still_goes_to_login(client):
    r = client.get("/interview-prep")
    assert r.status_code in (301, 302) and "login" in r.headers.get("Location", "").lower()


def test_env_var_replaces_the_list(auth_client, app, monkeypatch):
    monkeypatch.setenv("PREP_USER_EMAILS", "friend@example.com")
    _as(app, "venghatesh@gmail.com")
    assert auth_client.get("/java").status_code == 404
    _as(app, "friend@example.com")
    assert auth_client.get("/java").status_code == 200
