"""Query understanding: language detection, category detection, product matching.

Combines three signals (not keyword matching alone):
1. Registry product/alias matching  ("pressure cooker" -> Product row)
2. Standard-number pattern lookup   ("is 14543" -> StandardMetadata/product)
3. Category keyword scoring incl. Hindi (translit + Devanagari)

The detected category is used as a *boost* in retrieval (see reranker), not a
hard filter, so semantic similarity can still surface relevant chunks from
adjoining categories — while generic BIS questions (no category signal)
search everything.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.knowledge.registry import (
    CATEGORIES,
    PRODUCTS,
    normalize_category,
)
from app.logging_config import get_logger

logger = get_logger("app.rag.query_understanding")

# Devanagari Unicode range
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")


@dataclass
class QueryUnderstanding:
    raw_query: str
    language: str = "en"  # en | hi
    category: str = "general_bis"  # canonical key; "general_bis" = no signal
    category_confidence: float = 0.0
    product_name: str = ""  # matched registry product, if any
    standard_number: str = ""  # IS number explicitly mentioned in the query
    matched_keywords: list[str] = field(default_factory=list)

    @property
    def category_label(self) -> str:
        cat = CATEGORIES.get(self.category)
        return cat.label if cat else "General BIS"


def detect_language(text: str) -> str:
    """Hindi if Devanagari script is present, else English."""
    return "hi" if _DEVANAGARI_RE.search(text or "") else "en"


_STD_NUM_RE = re.compile(
    r"\bIS\s*/?\s*:?\s*(\d{2,5})(?:\s*(?:part|pt)?\s*[-/]?\s*(\d{1,2}))?\s*[:：]?\s*(\d{4})?\b",
    re.IGNORECASE,
)


def extract_standard_number(query: str) -> str:
    """Find an explicit 'IS 1234' / 'IS 14543:2015' reference in the query."""
    m = _STD_NUM_RE.search(query or "")
    if not m:
        return ""
    num = m.group(1)
    part = f"-{m.group(2)}" if m.group(2) else ""
    return f"IS {num}{part}"


# Question intents that signal "consumer guidance" phrasing — used to prefer
# consumer-checklist content in retrieval (weighting happens in the reranker).
_CONSUMER_GUIDANCE_TERMS = (
    "check before buying", "before buying", "what should i check", "look for",
    "how do i know", "how to identify", "verify", "kaise pehchane",
    "kya dekhein", "kya dhyan",
)


def understand_query(query: str) -> QueryUnderstanding:
    """Classify a user query into category/product/language understanding."""
    q = (query or "").lower()
    u = QueryUnderstanding(raw_query=query or "")

    if not q.strip():
        return u

    u.language = detect_language(query)

    # 1) explicit standard number -> trust it most ("is 14543" is unambiguous)
    u.standard_number = extract_standard_number(query)
    if u.standard_number:
        for p in PRODUCTS:
            if p.standard_number and p.standard_number.lower().startswith(
                u.standard_number.lower()
            ):
                u.product_name = p.name
                u.category = normalize_category(p.category)
                u.category_confidence = 0.95
                u.matched_keywords.append(u.standard_number.lower())
                return u
        # number not in registry — still a strong general_bis/standards signal
        u.category = "general_bis"
        u.category_confidence = 0.7
        u.matched_keywords.append(u.standard_number.lower())
        return u

    # 2) registry product/alias match (whole-token-ish, longest alias wins)
    from app.knowledge.registry import find_product

    product = find_product(query)
    if product:
        u.product_name = product.name
        u.category = normalize_category(product.category)
        u.category_confidence = 0.9
        u.matched_keywords.append(product.name.lower())
        # fall through to keyword scoring only to enrich matched_keywords

    # 3) keyword scoring across categories (English + Hindi)
    scores: dict[str, float] = {}
    for key, cat in CATEGORIES.items():
        score = 0.0
        for kw in cat.keywords:
            kw_l = kw.lower()
            if not kw_l:
                continue
            if " " in kw_l or _DEVANAGARI_RE.search(kw_l):
                # multi-word / script keywords: substring match, heavier weight
                if kw_l in q:
                    score += 2.0
                    if key not in (u.category,) and kw_l not in u.matched_keywords:
                        u.matched_keywords.append(kw_l)
            else:
                # single word: token match (avoids "is" matching "this")
                if re.search(r"(?<![a-z0-9])" + re.escape(kw_l) + r"(?![a-z0-9])", q):
                    score += 1.0
                    if kw_l not in u.matched_keywords:
                        u.matched_keywords.append(kw_l)
        if score:
            scores[key] = score

    if scores:
        best_key, best_score = max(scores.items(), key=lambda kv: kv[1])
        if u.product_name:
            # product match dominates unless keyword evidence is overwhelming
            if best_score > u.category_confidence * 4:
                u.category = normalize_category(best_key)
                u.category_confidence = min(0.85, best_score / 6)
        else:
            u.category = normalize_category(best_key)
            u.category_confidence = min(0.85, best_score / 6)

    logger.info(
        "query understanding: lang=%s category=%s (%.2f) product=%r std=%r",
        u.language, u.category, u.category_confidence, u.product_name,
        u.standard_number,
    )
    return u


def is_consumer_guidance_query(query: str) -> bool:
    q = (query or "").lower()
    return any(t in q for t in _CONSUMER_GUIDANCE_TERMS)
