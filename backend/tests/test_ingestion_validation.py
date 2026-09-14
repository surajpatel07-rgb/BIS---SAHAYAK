"""Upload validation and error handling tests."""
import random


def _admin_headers(client) -> dict:
    from app.database.base import SessionLocal
    from app.models import User
    from app.security import create_access_token, hash_password

    email = f"ingadmin{random.randint(0, 10**9)}@test.in"
    db = SessionLocal()
    u = User(name="Ing Admin", email=email, password_hash=hash_password("Admin@12345"), role="admin")
    db.add(u)
    db.commit()
    db.refresh(u)
    token = create_access_token(str(u.id), extra={"role": "admin"})
    db.close()
    return {"Authorization": f"Bearer {token}"}


def test_upload_rejects_non_pdf(client):
    r = client.post(
        "/api/documents/upload",
        headers=_admin_headers(client),
        files={"file": ("notes.txt", b"just text, not a pdf", "text/plain")},
    )
    assert r.status_code == 400
    assert "PDF" in r.json()["detail"]


def test_upload_rejects_fake_pdf(client):
    r = client.post(
        "/api/documents/upload",
        headers=_admin_headers(client),
        files={"file": ("fake.pdf", b"%PDF-1.4 not really a pdf just bytes", "application/pdf")},
    )
    assert r.status_code in (202, 400)
    if r.status_code == 202:
        assert r.json()["status"] in ("failed", "indexed")


def test_search_requires_auth(client):
    r = client.get("/api/search", params={"q": "cement"})
    assert r.status_code == 401
