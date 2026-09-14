"""Authentication and authorization tests."""
import random


def test_register_login_me(client, user_token):
    headers, _ = user_token
    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["role"] == "user"


def test_duplicate_register_rejected(client, user_token):
    email = f"dup{random.randint(0, 10**9)}@test.in"
    r = client.post(
        "/api/auth/register",
        json={"name": "Dup User", "email": email, "password": "Test@12345"},
    )
    assert r.status_code == 201
    r = client.post(
        "/api/auth/register",
        json={"name": "Dup User", "email": email, "password": "Test@12345"},
    )
    assert r.status_code == 409


def test_wrong_password_rejected(client, user_token):
    r = client.post(
        "/api/auth/login", json={"email": "nobody@nowhere.in", "password": "wrongpass"}
    )
    assert r.status_code == 401


def test_documents_require_auth(client):
    r = client.get("/api/documents")
    assert r.status_code == 401


def test_admin_routes_require_admin(client, user_token):
    headers, _ = user_token
    r = client.get("/api/admin/stats", headers=headers)
    assert r.status_code == 403
    r = client.post(
        "/api/documents/upload", headers=headers, files={"file": ("x.pdf", b"%PDF-1.4 test")}
    )
    assert r.status_code == 403
