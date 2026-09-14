"""RAG integration tests: ingestion -> retrieval -> chat -> citations.

Runs fully offline with the hash embedding provider + extractive fallback LLM.
"""
from __future__ import annotations

import random

from app.database.base import SessionLocal
from app.ingestion.service import ingest_document
from app.models import Document


def _seed_pdf(client, tmp_name: str, body: str) -> int:
    """Upload a small generated PDF through the API and return its document id."""
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), body, fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()

    admin = _admin_headers(client)
    r = client.post(
        "/api/documents/upload",
        headers=admin,
        files={"file": (tmp_name, pdf_bytes, "application/pdf")},
        data={"title": tmp_name, "standard_number": "IS 9999:2025"},
    )
    assert r.status_code == 202, r.text
    return r.json()["id"]


def _admin_headers(client) -> dict:
    from app.database.base import SessionLocal
    from app.models import User
    from app.security import create_access_token, hash_password

    email = f"ragadmin{random.randint(0, 10**9)}@test.in"
    db = SessionLocal()
    u = User(name="RAG Admin", email=email, password_hash=hash_password("Admin@12345"), role="admin")
    db.add(u)
    db.commit()
    db.refresh(u)
    token = create_access_token(str(u.id), extra={"role": "admin"})
    db.close()
    return {"Authorization": f"Bearer {token}"}


def _user_headers(client) -> dict:
    email = f"raguser{random.randint(0, 10**9)}@test.in"
    r = client.post(
        "/api/auth/register",
        json={"name": "RAG User", "email": email, "password": "Test@12345"},
    )
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_full_rag_flow_with_citations(client):
    """Question -> retrieval -> context -> answer -> citation, offline end-to-end."""
    body = (
        "4. REQUIREMENTS\n\n"
        "The device shall operate at a voltage of 230 volts. "
        "The insulation resistance shall not be less than 50 megaohms. "
        "The device shall pass a dielectric strength test at 2000 volts for one minute.\n\n"
        "5. MARKING\n\n"
        "The product shall be marked with the ISI mark under a valid BIS licence."
    )
    doc_id = _seed_pdf(client, "test_voltage_standard.pdf", body)

    # Wait-free: upload endpoint ingests synchronously.
    db = SessionLocal()
    d = db.get(Document, doc_id)
    assert d.status == "indexed", d.error_message
    db.close()

    headers = _user_headers(client)
    r = client.post(
        "/api/chat",
        headers=headers,
        json={
            "message": "What is the insulation resistance requirement?",
            "mode": "industry",
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["answer"], "answer must not be empty"
    assert isinstance(data["sources"], list)
    assert len(data["sources"]) >= 1, "expected at least one citation"
    src = data["sources"][0]
    assert src["standard_number"] == "IS 9999:2025"
    assert src["page"] >= 1
    assert 0 <= src["relevance_score"] <= 1

    # Conversation persisted with both messages
    r2 = client.get(f"/api/conversations/{data['conversation_id']}", headers=headers)
    assert r2.status_code == 200
    msgs = r2.json()["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant"]


def test_grounded_refusal_when_no_matching_content(client):
    """The assistant must not invent requirements for out-of-corpus questions."""
    headers = _user_headers(client)
    r = client.post(
        "/api/chat",
        headers=headers,
        json={
            "message": "zzzqxv bajamba florquet wibblewobble kwargnific?,".rstrip(","),
            "mode": "industry",
        },
    )
    assert r.status_code == 200
    data = r.json()
    # Fallback provider refuses when no sentence matches the query terms.
    assert "could not find sufficient information" in data["answer"].lower() or (
        len(data["sources"]) == 0
    )


def test_semantic_search_returns_chunk_hits(client):
    body = (
        "2. TEST METHODS\n\n"
        "The tensile strength shall be determined using a calibrated universal "
        "testing machine at a loading rate of 10 mm per minute."
    )
    _seed_pdf(client, "test_tensile_standard.pdf", body)
    headers = _user_headers(client)
    r = client.get("/api/search", params={"q": "tensile strength testing machine"}, headers=headers)
    assert r.status_code == 200
    hits = r.json()["results"]
    assert len(hits) >= 1
    assert hits[0]["page"] >= 1
    assert "tensile" in hits[0]["snippet"].lower()
