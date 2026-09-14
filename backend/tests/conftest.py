"""Shared pytest fixtures."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Fresh isolated DB for each test session (remove leftovers from prior runs)
_TEST_DB = BACKEND_DIR.parent / "data" / "test_bisbuddy.db"
if _TEST_DB.exists():
    _TEST_DB.unlink()
os.environ["DATABASE_URL"] = "sqlite:///./data/test_bisbuddy.db"
os.environ["GEMINI_API_KEY"] = ""  # force fallback LLM (no network)
os.environ["EMBEDDING_PROVIDER"] = "hash"  # keep embeddings offline even if .env says gemini
os.environ["SECRET_KEY"] = "test-secret-key"


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.database.base import Base, engine
    from app.main import app

    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    # Clean tables between tests is handled per-test via unique emails.


@pytest.fixture()
def user_token(client):
    """Register + login a normal user, return (headers, user_id)."""
    import random

    email = f"u{random.randint(0, 10**9)}@test.in"
    r = client.post(
        "/api/auth/register",
        json={"name": "Test User", "email": email, "password": "Test@12345"},
    )
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    user_id = r.json()["user"]["id"]
    return {"Authorization": f"Bearer {token}"}, user_id


@pytest.fixture()
def admin_token(client):
    """Create an admin user directly in DB, return headers."""
    import random

    from app.database.base import SessionLocal
    from app.models import User
    from app.security import create_access_token, hash_password

    email = f"admin{random.randint(0, 10**9)}@test.in"
    db = SessionLocal()
    user = User(
        name="Admin", email=email, password_hash=hash_password("Admin@12345"), role="admin"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(str(user.id), extra={"role": "admin"})
    db.close()
    return {"Authorization": f"Bearer {token}"}
