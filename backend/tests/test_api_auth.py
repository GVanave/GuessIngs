from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import register


def test_register_sets_httponly_session_and_csrf_cookie(client):
    res = client.post("/api/auth/register", json={"email": "A@Example.com", "password": "Passw0rd!"})
    assert res.status_code == 201
    body = res.json()
    assert body["user"]["email"] == "a@example.com"
    assert "password" not in str(body["user"]).lower()
    cookies = res.headers.get_list("set-cookie")
    session = next(c for c in cookies if c.startswith("gi_session="))
    assert "HttpOnly" in session and "SameSite=lax" in session
    assert any(c.startswith("gi_csrf=") and "HttpOnly" not in c for c in cookies)


def test_duplicate_email_is_rejected_case_insensitively(client):
    register(client, "dup@example.com")
    res = client.post("/api/auth/register", json={"email": "DUP@example.com", "password": "Passw0rd!"})
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "email_taken"


def test_weak_password_and_invalid_email_are_rejected(client):
    res = client.post("/api/auth/register", json={"email": "x@example.com", "password": "short"})
    assert res.status_code == 422
    assert "at least 8" in res.json()["error"]["message"]
    res = client.post("/api/auth/register", json={"email": "x@example.com", "password": "longbutnodigits"})
    assert res.status_code == 422
    res = client.post("/api/auth/register", json={"email": "not-an-email", "password": "Passw0rd!"})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "validation_error"


def test_login_success_and_failure(client):
    register(client, "login@example.com")
    client.cookies.clear()
    bad = client.post("/api/auth/login", json={"email": "login@example.com", "password": "Wrong1234"})
    assert bad.status_code == 401
    unknown = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "Wrong1234"})
    assert unknown.status_code == 401
    assert bad.json() == unknown.json()  # no account enumeration
    ok = client.post("/api/auth/login", json={"email": "LOGIN@example.com", "password": "Passw0rd!"})
    assert ok.status_code == 200


def test_protected_routes_require_authentication(client):
    for method, path in [("get", "/api/auth/me"), ("get", "/api/analyses"), ("get", "/api/dashboard"),
                         ("post", "/api/analyses"), ("get", "/api/products/saved")]:
        res = getattr(client, method)(path)
        assert res.status_code == 401, path
        assert res.json()["error"]["code"] == "not_authenticated"


def test_invalid_token_is_rejected(client):
    res = client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.token"})
    assert res.status_code == 401


def test_cookie_session_requires_csrf_header_for_mutations(client):
    register(client)
    del client.headers["X-CSRF-Token"]
    res = client.post("/api/analyses", json={"ingredients_text": "oats"})
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "csrf_failed"
    res = client.post("/api/analyses", json={"ingredients_text": "oats"}, headers={"X-CSRF-Token": "forged"})
    assert res.status_code == 403
    assert client.get("/api/auth/me").status_code == 200  # safe methods don't need the token


def test_bearer_token_clients_do_not_need_csrf():
    with TestClient(app) as c:
        token = register(c)["access_token"]
        c.cookies.clear()
        res = c.post("/api/analyses", json={"ingredients_text": "oats"}, headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 201


def test_logout_clears_session(client):
    register(client)
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_password_change_revokes_old_tokens(client):
    old_token = register(client)["access_token"]
    res = client.post("/api/users/me/password", json={"current_password": "Passw0rd!", "new_password": "NewPassw0rd"})
    assert res.status_code == 200
    client.headers["X-CSRF-Token"] = client.cookies.get("gi_csrf")
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {old_token}"}).status_code == 401
    assert client.get("/api/auth/me").status_code == 200
    wrong = client.post("/api/users/me/password", json={"current_password": "nope", "new_password": "NewPassw0rd2"})
    assert wrong.status_code == 400


def test_profile_update_and_preferences_validation(auth_client):
    res = auth_client.patch("/api/users/me", json={"full_name": "  Ada   Lovelace ", "preferences": {"theme": "dark"}})
    assert res.status_code == 200
    assert res.json()["full_name"] == "Ada Lovelace"
    assert res.json()["preferences"]["theme"] == "dark"
    bad = auth_client.patch("/api/users/me", json={"preferences": {"theme": "neon"}})
    assert bad.status_code == 422
    extra = auth_client.patch("/api/users/me", json={"preferences": {"is_admin": True}})
    assert extra.status_code == 422


def test_delete_account_requires_password(auth_client):
    assert auth_client.request("DELETE", "/api/users/me", json={"password": "wrong"}).status_code == 400
    assert auth_client.request("DELETE", "/api/users/me", json={"password": "Passw0rd!"}).status_code == 204
    assert auth_client.get("/api/auth/me").status_code == 401


def test_login_is_rate_limited(client, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_AUTH_PER_MINUTE", "3")
    from app.core.config import get_settings
    get_settings.cache_clear()
    codes = [client.post("/api/auth/login", json={"email": "a@example.com", "password": "x"}).status_code for _ in range(5)]
    assert codes[:3] == [401, 401, 401]
    assert codes[3:] == [429, 429]
    res = client.post("/api/auth/login", json={"email": "a@example.com", "password": "x"})
    assert res.headers["retry-after"] == "60"
    assert res.json()["error"]["code"] == "rate_limited"


def test_security_headers_present(client):
    res = client.get("/api/meta/scoring-rules")
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["x-frame-options"] == "DENY"
    assert "default-src 'none'" in res.headers["content-security-policy"]
