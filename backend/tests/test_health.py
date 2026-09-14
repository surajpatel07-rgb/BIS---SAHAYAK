"""Health endpoint tests."""


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["app"] == "BIS Buddy API"


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True
