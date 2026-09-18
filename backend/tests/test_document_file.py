"""Tests for the document PDF file endpoint (citation → actual PDF flow).

Covers the three auth paths (session header, scoped query token, none), the
content-type/disposition contract, cross-document token rejection, the
file-token minting endpoint, and missing-file behaviour.
"""
from __future__ import annotations

import io

import pytest


def _pdf_bytes() -> bytes:
    """A minimal but REAL one-page PDF with extractable text (pymupdf)."""
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Citation test standard. Scope: covers test requirements.")
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


@pytest.fixture()
def pdf_document(client):
    """Create a Document row + real PDF in uploads, then run ingestion."""
    from app.config import settings
    from app.database.base import SessionLocal
    from app.ingestion.service import ingest_document
    from app.models import Document

    db = SessionLocal()
    try:
        doc = Document(
            name="Citation Test — Spec (SAMPLE).pdf",  # non-ascii name on purpose
            standard_number="IS 9999",
            title="Citation Test Spec",
            category="general_bis",
            document_type="standard",
            status="uploaded",
            description="test",
            file_path="",
            file_size=0,
            page_count=1,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        stored = settings.uploads_path / f"citation-test-{doc.id}.pdf"
        data = _pdf_bytes()
        stored.write_bytes(data)
        doc.file_path = str(stored)
        doc.file_size = len(data)
        db.commit()
        ingested = ingest_document(db, doc.id)
        assert ingested.status == "indexed"
        yield doc.id
    finally:
        db.close()


@pytest.fixture()
def auth_headers(user_token):
    headers, _ = user_token
    return headers


class TestFileEndpoint:
    def test_requires_auth(self, client, pdf_document):
        r = client.get(f"/api/documents/{pdf_document}/file")
        assert r.status_code == 401

    def test_serves_pdf_with_bearer(self, client, auth_headers, pdf_document):
        r = client.get(f"/api/documents/{pdf_document}/file", headers=auth_headers)
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert r.headers["content-disposition"].startswith("inline")
        assert r.content.startswith(b"%PDF")

    def test_serves_pdf_with_scoped_query_token(self, client, auth_headers, pdf_document):
        mint = client.post(
            f"/api/documents/{pdf_document}/file-token", headers=auth_headers
        )
        assert mint.status_code == 200
        token = mint.json()["token"]
        # No Authorization header — exactly what a citation tab sends.
        r = client.get(f"/api/documents/{pdf_document}/file?token={token}")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert r.content.startswith(b"%PDF")

    def test_token_rejected_for_other_document(self, client, auth_headers, pdf_document):
        mint = client.post(
            f"/api/documents/{pdf_document}/file-token", headers=auth_headers
        )
        token = mint.json()["token"]
        r = client.get(f"/api/documents/{pdf_document + 100}/file?token={token}")
        assert r.status_code == 403
        assert "Source unavailable" in r.text

    def test_garbage_token_rejected(self, client, pdf_document):
        r = client.get(f"/api/documents/{pdf_document}/file?token=not-a-jwt")
        assert r.status_code == 401
        assert "Source unavailable" in r.text

    def test_token_minting_requires_auth(self, client, pdf_document):
        r = client.post(f"/api/documents/{pdf_document}/file-token")
        assert r.status_code == 401

    def test_nonascii_name_disposition_is_header_safe(self, client, auth_headers, pdf_document):
        r = client.get(f"/api/documents/{pdf_document}/file", headers=auth_headers)
        assert r.status_code == 200
        disposition = r.headers["content-disposition"]
        # RFC 5987 filename* present; raw header must be latin-1 encodable
        assert "filename*=UTF-8''" in disposition
        disposition.encode("latin-1")  # would raise UnicodeEncodeError before the fix

    def test_missing_file_is_friendly_html(self, client, auth_headers):
        """Missing on-disk file -> friendly 'Source unavailable' HTML page, not JSON/blank."""
        r = client.get("/api/documents/999999/file", headers=auth_headers)
        assert r.status_code == 404
        assert "Source unavailable" in r.text
        assert "text/html" in r.headers["content-type"]

    def test_unauthenticated_gets_friendly_html(self, client, pdf_document):
        """Expired/absent auth -> styled sign-in prompt, never a bare JSON API page."""
        r = client.get(f"/api/documents/{pdf_document}/file")
        assert r.status_code == 401
        assert "Source unavailable" in r.text
        assert "Sign-in required" in r.text
