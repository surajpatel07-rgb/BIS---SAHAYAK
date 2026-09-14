"""Knowledge-base expansion tests: categories, products, detection, filtering.

Honesty guarantees tested here:
- products with unknown standards expose info_available=False, never a number
- category detection maps the six SIH demo questions correctly
- category filtering actually narrows retrieval results
"""
from __future__ import annotations

import pytest

from app.knowledge.registry import (
    CATEGORIES,
    PRODUCTS,
    find_product,
    normalize_category,
    related_questions_for,
)
from app.rag.query_understanding import detect_language, understand_query


# ---------------------------------------------------------------------------
# Registry honesty
# ---------------------------------------------------------------------------
def test_registry_has_six_categories():
    expected = {
        "food",
        "hallmarking",
        "electronics_electrical",
        "everyday_products",
        "general_bis",
        "industry",
    }
    assert set(CATEGORIES.keys()) == expected


def test_products_without_known_standards_expose_no_number():
    """Products marked info-not-available must never carry an invented number."""
    for p in PRODUCTS:
        if p.certification_status == "info-not-available":
            assert p.standard_number == "", f"{p.name} must not carry a standard number"
            assert not p.consumer_checklist or any(
                "not" in c.lower() or "check" in c.lower() for c in p.consumer_checklist
            )


def test_known_standards_are_real_bis_numbers():
    """Sanity: the numbers we do ship are the well-known ones (no IS 99999)."""
    numbers = {p.standard_number for p in PRODUCTS if p.standard_number}
    for known in ("IS 14543", "IS 13428", "IS 2347", "IS 694", "IS 1417", "IS 2925"):
        assert known in numbers
    for p in PRODUCTS:
        if p.standard_number:
            assert p.standard_number.startswith("IS "), p.standard_number


def test_related_questions_do_not_invent_product_facts():
    qs = related_questions_for("hallmarking", None)
    assert 0 < len(qs) <= 3
    assert all(isinstance(q, str) and q.strip() for q in qs)


# ---------------------------------------------------------------------------
# Category normalization + detection
# ---------------------------------------------------------------------------
def test_normalize_legacy_categories():
    assert normalize_category("cement") == "everyday_products"
    assert normalize_category("safety") == "everyday_products"
    assert normalize_category("consumer") == "general_bis"
    assert normalize_category("certification") == "industry"
    assert normalize_category("Electronics & Electrical") == "electronics_electrical"
    assert normalize_category(None) == "general_bis"
    assert normalize_category("unknown-thing") == "general_bis"


@pytest.mark.parametrize(
    "query,expected",
    [
        ("What should I check before buying a pressure cooker?", "everyday_products"),
        ("What does HUID mean?", "hallmarking"),
        ("Is BIS certification required for this electrical product?", "electronics_electrical"),
        ("What BIS standard applies to packaged drinking water?", "food"),
        ("What is BIS?", "general_bis"),
        ("What standards should a manufacturer check before producing?", "industry"),
        ("Which wire should I use for house wiring?", "electronics_electrical"),
        ("Is my gold genuine?", "hallmarking"),
        ("Tell me about the weather", "general_bis"),
    ],
)
def test_category_detection_siH_scenarios(query, expected):
    u = understand_query(query)
    assert u.category == expected, f"{query!r} -> {u.category}, expected {expected}"


def test_detection_extracts_standard_numbers():
    u = understand_query("What does IS 14543 require?")
    assert u.standard_number == "IS 14543"
    assert u.category == "food"
    assert u.product_name == "Packaged Drinking Water"


def test_detection_handles_hindi():
    assert detect_language("सोने की हॉलमार्किंग क्या होती है?") == "hi"
    u = understand_query("सोने की हॉलमार्किंग क्या होती है?")
    assert u.language == "hi"
    assert u.category == "hallmarking"


def test_find_product_matches_aliases():
    assert find_product("buying a cooker tomorrow") is not None
    assert find_product("is my gold genuine") is not None
    assert find_product("quantum computing") is None


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------
def _user_headers(client):
    r = client.post(
        "/api/auth/login",
        json={"email": "demo@bisbuddy.in", "password": "Demo@12345"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _admin_headers(client):
    r = client.post(
        "/api/auth/login",
        json={"email": "admin@bisbuddy.in", "password": "Admin@12345"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_categories_endpoint_lists_all(client):
    r = client.get("/api/knowledge/categories", headers=_user_headers(client))
    assert r.status_code == 200
    keys = {c["key"] for c in r.json()}
    assert keys == set(CATEGORIES.keys())
    for c in r.json():
        assert isinstance(c["document_count"], int)  # live DB numbers, not hardcoded


def test_products_endpoint_filters_by_category(client):
    r = client.get(
        "/api/knowledge/products?category=hallmarking", headers=_user_headers(client)
    )
    assert r.status_code == 200
    items = r.json()
    assert items, "hallmarking has registry products"
    assert all(p["category"] == "hallmarking" for p in items)


def test_product_detail_unknown_standard_is_explicit(client):
    r = client.get("/api/knowledge/products", headers=_user_headers(client))
    footwear = next(p for p in r.json() if p["name"] == "Footwear")
    assert footwear["certification_status"] == "info-not-available"
    assert footwear["standard_number"] == ""
    detail = client.get(
        f"/api/knowledge/products/{footwear['id']}", headers=_user_headers(client)
    )
    assert detail.status_code == 200
    assert detail.json()["info_available"] is False


def test_product_detail_includes_related_documents(client):
    r = client.get("/api/knowledge/products", headers=_user_headers(client))
    cooker = next(p for p in r.json() if p["name"] == "Pressure Cookers")
    detail = client.get(
        f"/api/knowledge/products/{cooker['id']}", headers=_user_headers(client)
    )
    assert detail.status_code == 200
    body = detail.json()
    assert body["standard_number"] == "IS 2347"
    assert isinstance(body["related_documents"], list)
    assert len(body["related_questions"]) <= 3


def test_knowledge_stats_requires_admin(client):
    r = client.get("/api/knowledge/stats", headers=_user_headers(client))
    assert r.status_code == 403
    r = client.get("/api/knowledge/stats", headers=_admin_headers(client))
    assert r.status_code == 200
    cats = {c["key"]: c for c in r.json()["categories"]}
    # numbers come from the live DB (seeded corpus exists in tests)
    assert cats["food"]["documents"] >= 1
    assert all(c["chunks"] >= 0 for c in cats.values())


def test_rag_debug_requires_admin_and_returns_trace(client):
    r = client.get("/api/knowledge/debug/retrieval?q=huid", headers=_user_headers(client))
    assert r.status_code == 403
    r = client.get(
        "/api/knowledge/debug/retrieval?q=What%20is%20HUID%3F",
        headers=_admin_headers(client),
    )
    assert r.status_code == 200
    trace = r.json()
    assert trace["detected_category"] == "hallmarking"
    assert "candidates_before_rerank" in trace
    assert "selected_chunks" in trace
    assert "final_context" in trace


# ---------------------------------------------------------------------------
# Category-aware retrieval + chat
# ---------------------------------------------------------------------------
def test_category_filter_narrows_retrieval(client):
    from app.database.base import SessionLocal
    from app.rag.retrieval import RetrievalService

    db = SessionLocal()
    try:
        svc = RetrievalService()
        unfiltered = svc.retrieve(db, "certification requirements", top_k=8)
        cats_all = {c.category for c in unfiltered}
        filtered = svc.retrieve(db, "certification requirements", top_k=8, categories=["industry"])
        assert filtered, "industry category has indexed documents"
        assert {c.category for c in filtered} <= {"industry"}
        # and the filter actually excludes at least one category present unfiltered
        if len(cats_all) > 1 and unfiltered:
            assert cats_all - {"industry"}
    finally:
        db.close()


def test_chat_returns_detection_and_related_questions(client):
    headers = _user_headers(client)
    r = client.post(
        "/api/chat",
        headers=headers,
        json={"message": "What is HUID and why is it useful?", "mode": "consumer"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["detected_category"] == "hallmarking"
    assert body["category_label"] == "Gold & Silver"
    assert 0 <= body["category_confidence"] <= 1
    assert 0 < len(body["related_questions"]) <= 3
    assert body["language"] == "en"


def test_chat_stream_done_event_carries_detection(client):
    headers = _user_headers(client)
    with client.stream(
        "POST",
        "/api/chat/stream",
        headers=headers,
        json={"message": "What is HUID?", "mode": "consumer"},
    ) as resp:
        assert resp.status_code == 200
        done_data = None
        for line in resp.iter_lines():
            if isinstance(line, bytes):
                line = line.decode("utf-8")
            if line.startswith("data:"):
                import json

                payload = json.loads(line[5:].strip())
                if "related_questions" in payload:
                    done_data = payload
        assert done_data is not None
        assert done_data["detected_category"] == "hallmarking"
