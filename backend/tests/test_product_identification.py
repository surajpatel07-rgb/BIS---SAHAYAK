"""Tests for the AI Product Identifier feature.

Covers: image validation, quality flags, query bridging, the match-standard
endpoint (offline, real RAG over the seeded corpus), auth requirements, and
the no-fabrication guarantee (standards only from retrieved chunks).
"""
from __future__ import annotations

import io

import pytest

from app.rag.vision import (
    Identification,
    VisionError,
    identification_to_query,
    image_quality_flags,
    validate_image,
)


# ---- helpers -----------------------------------------------------------------
@pytest.fixture()
def auth_headers(user_token):
    """user_token yields (headers, user_id); tests here only need headers."""
    headers, _ = user_token
    return headers


def _png_bytes(w=320, h=240, color=(120, 120, 120)) -> bytes:
    """Build a real PNG in memory (Pillow is installed for vision)."""
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture()
def indexed_corpus(client):
    """Seed a small set of indexed documents + chunks directly (offline)."""
    from app.database.base import SessionLocal
    from app.models import Document, DocumentChunk
    from app.rag.embeddings import get_embedding_provider

    provider = get_embedding_provider()
    db = SessionLocal()
    docs = [
        ("Cooker-GUIDE.pdf", "everyday_products", "IS 2346", "Pressure cookers guide",
         ["Pressure cookers are covered under mandatory BIS certification; look for "
          "the ISI mark on the lid before buying a pressure cooker."]),
        ("ELEC-GUIDE.pdf", "electronics_electrical", "IS 302", "Electrical safety guide",
         ["Household electrical appliances must meet insulation and earthing safety "
          "requirements; check the ISI mark on electric kettles and irons."]),
        ("WATER-GUIDE.pdf", "food", "IS 14543", "Packaged drinking water",
         ["Packaged drinking water carries mandatory BIS certification; the IS 14543 "
          "standard applies to bottled drinking water."]),
    ]
    try:
        for name, cat, std, title, paras in docs:
            doc = Document(
                name=name, standard_number=std, title=title, category=cat,
                document_type="guide", status="indexed", description="test doc",
                file_path="tests", file_size=1, page_count=1,
            )
            db.add(doc)
            db.flush()
            for i, para in enumerate(paras):
                chunk = DocumentChunk(
                    document_id=doc.id,
                    chunk_id=i + 1,
                    chunk_text=para,
                    page_number=i + 1,
                    section=f"Section {i + 1}",
                    embedding=provider.embed([para])[0],
                )
                db.add(chunk)
        db.commit()
        yield
    finally:
        # keep the session-scoped DB; tables are per-test unique-keyed
        db.close()


# ---- validation & heuristics ---------------------------------------------------
class TestImageValidation:
    def test_rejects_empty(self):
        with pytest.raises(VisionError):
            validate_image(b"", "a.png", "image/png")

    def test_rejects_oversize(self):
        big = b"x" * (9 * 1024 * 1024)
        with pytest.raises(VisionError, match="too large"):
            validate_image(big, "a.jpg", "image/jpeg")

    def test_rejects_bad_type(self):
        data = _png_bytes()
        with pytest.raises(VisionError, match="Unsupported image format"):
            validate_image(data, "malware.exe", "application/octet-stream")

    @pytest.mark.parametrize(
        "fname,ctype",
        [("a.jpg", "image/jpeg"), ("b.png", "image/png"), ("c.webp", "image/webp"),
         ("d.jpeg", "image/jpg"), ("e.png", "")],
    )
    def test_accepts_common_formats(self, fname, ctype):
        out = validate_image(_png_bytes(), fname, ctype)
        assert out in ("image/jpeg", "image/png", "image/webp")

    def test_quality_flags_dark_image(self):
        flags = image_quality_flags(_png_bytes(color=(3, 3, 3)))
        assert any("dark" in f for f in flags)

    def test_quality_flags_blank_image(self):
        flags = image_quality_flags(_png_bytes(color=(200, 200, 200)))
        assert any("blank" in f or "featureless" in f for f in flags)

    def test_quality_flags_small_image(self):
        flags = image_quality_flags(_png_bytes(w=40, h=40))
        assert any("small" in f for f in flags)

    def test_quality_flags_clean_image(self):
        # a textured, reasonably bright image
        from PIL import Image

        img = Image.new("RGB", (320, 240))
        px = img.load()
        for y in range(240):
            for x in range(320):
                px[x, y] = ((x * 7) % 256, (y * 5) % 256, ((x + y) * 3) % 256)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        assert image_quality_flags(buf.getvalue()) == []


# ---- query bridging -------------------------------------------------------------
class TestQueryBridge:
    def test_query_includes_product(self):
        ident = Identification(product_name="electric kettle", confidence=0.9)
        q = identification_to_query(ident)
        assert "electric kettle" in q.lower()
        assert "BIS" in q

    def test_query_falls_back_to_description(self):
        ident = Identification(product_name="", confidence=0.1)
        q = identification_to_query(ident, "stainless steel flask")
        assert "stainless steel flask" in q.lower()

    def test_query_includes_markings(self):
        ident = Identification(
            product_name="pressure cooker", confidence=0.8, markings=["ISI mark"]
        )
        assert "ISI mark" in identification_to_query(ident)


# ---- matching endpoint (offline, real RAG) ---------------------------------------
class TestMatchStandardEndpoint:
    def test_requires_auth(self, client):
        r = client.post(
            "/api/product-identification/match-standard",
            json={"product_name": "pressure cooker"},
        )
        assert r.status_code == 401

    def test_name_too_short(self, client, auth_headers):
        r = client.post(
            "/api/product-identification/match-standard",
            json={"product_name": "x"},
            headers=auth_headers,
        )
        assert r.status_code == 422

    def test_match_returns_retrieved_standards_only(self, client, auth_headers, indexed_corpus):
        r = client.post(
            "/api/product-identification/match-standard",
            json={"product_name": "pressure cooker"},
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        # The only "standards" are the ones we indexed above (real RAG).
        assert body["standards"], "expected at least one retrieved standard"
        for s in body["standards"]:
            assert s["document_id"] > 0
            assert s["evidence"], "evidence must come from the retrieved chunk"
            assert s["match_level"] in ("strong", "moderate", "weak")
            assert 0.0 <= s["confidence"] <= 1.0
        joined = " ".join(s["title"] for s in body["standards"]).lower()
        assert any(k in joined for k in ("cooker", "guide")), (
            "recommendations must come from indexed documents, not fabricated"
        )

    def test_unknown_product_is_honest(self, client, auth_headers, indexed_corpus):
        r = client.post(
            "/api/product-identification/match-standard",
            json={"product_name": "quantum flux capacitor xyz"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["standards"] == [] or body["needs_verification"]
        assert any("No sufficiently relevant" in w or "weakly relevant" in w
                   for w in body["warnings"])

    def test_response_shape(self, client, auth_headers, indexed_corpus):
        r = client.post(
            "/api/product-identification/match-standard",
            json={"product_name": "electric kettle"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert set(body.keys()) >= {
            "product", "standards", "warnings", "needs_verification",
            "query_used", "llm_provider",
        }
        assert body["product"]["confidence"] == 1.0  # user-confirmed name
        assert body["product"]["possible_matches"] == []
        assert body["query_used"].lower().startswith("bis standard")

    def test_category_note_in_query(self, client, auth_headers):
        r = client.post(
            "/api/product-identification/match-standard",
            json={"product_name": "insulated water bottle", "category": "food"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        q = r.json()["query_used"].lower()
        # Either the raw name or its registry-canonical product name appears.
        assert "water bottle" in q or "packaged drinking water" in q


# ---- identification endpoint ------------------------------------------------------
class TestIdentifyEndpoint:
    def test_requires_auth(self, client):
        r = client.post(
            "/api/product-identification",
            files={"image": ("kettle.png", _png_bytes(), "image/png")},
        )
        assert r.status_code == 401

    def test_rejects_invalid_type(self, client, auth_headers):
        r = client.post(
            "/api/product-identification",
            files={"image": ("virus.exe", b"MZ...", "application/octet-stream")},
            data={"description": ""},
            headers=auth_headers,
        )
        assert r.status_code == 400
        assert "Unsupported image format" in r.json()["detail"]

    def test_rejects_oversize(self, client, auth_headers):
        big = b"0" * (9 * 1024 * 1024)
        r = client.post(
            "/api/product-identification",
            files={"image": ("big.jpg", big, "image/jpeg")},
            headers=auth_headers,
        )
        assert r.status_code == 400
        assert "too large" in r.json()["detail"].lower()

    def test_offline_mode_is_transparent(self, client, auth_headers):
        """No GEMINI_API_KEY in tests: the endpoint must say so, not fake results."""
        r = client.post(
            "/api/product-identification",
            files={"image": ("kettle.png", _png_bytes(), "image/png")},
            headers=auth_headers,
        )
        assert r.status_code == 503
        assert "GEMINI_API_KEY" in r.json()["detail"] or "vision model" in r.json()["detail"].lower()
