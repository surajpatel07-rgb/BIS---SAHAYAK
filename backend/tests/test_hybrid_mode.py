"""Hybrid answer-mode tests: BIS-grounded (MODE A) vs general-knowledge (MODE B).

Runs offline: the classifier and post-processing are pure logic, and the
extractive fallback provider exercises MODE B transparency without network.
"""
from __future__ import annotations

from app.rag.llm import GENERAL_MARKER, detect_answer_mode, ensure_citations


# ---------------------------------------------------------------------------
# Classifier routing
# ---------------------------------------------------------------------------

def test_classifier_routes_bis_questions_to_grounded_mode():
    bis_questions = [
        "What are the BIS requirements for cement?",
        "How do I get BIS certification for my product?",
        "What is the setting time requirement in IS 1234:2020?",
        "Which standard applies to safety helmets?",
        "How can I verify the ISI mark on a product?",
        "What documents are required for factory licence registration?",
        "What is the tensile testing procedure?",
    ]
    for q in bis_questions:
        assert detect_answer_mode(q) == "bis", q


def test_classifier_routes_general_questions_to_general_mode():
    general_questions = [
        "What is the capital of France?",
        "Tell me a joke.",
        "How do I stay motivated while studying?",
        "Write an email to my manager",
        "What is 2 plus 2?",
        "What is the best way to learn programming?",
    ]
    for q in general_questions:
        assert detect_answer_mode(q) == "general", q


def test_classifier_bare_is_verb_is_not_a_standard_reference():
    # "is 2" is the verb + number, not an IS standard number.
    assert detect_answer_mode("what is 2 plus 2?") == "general"
    # "is 1234" looks like a standard number.
    assert detect_answer_mode("what is 1234?") == "bis"


def test_classifier_empty_question_is_general():
    assert detect_answer_mode("") == "general"
    assert detect_answer_mode("   ") == "general"


# ---------------------------------------------------------------------------
# Citation safety net + general marker interaction
# ---------------------------------------------------------------------------

def test_ensure_citations_skips_general_answers():
    answer = GENERAL_MARKER + " Paris is the capital of France."
    assert ensure_citations(answer, 3) == answer  # untouched


def test_ensure_citations_skips_refusals():
    answer = "I could not find sufficient information in the indexed BIS documents."
    assert ensure_citations(answer, 3) == answer  # untouched


def test_ensure_citations_appends_sources_to_markerless_grounded_answer():
    out = ensure_citations("Cement setting time is 30 minutes.", 3)
    assert "Sources: [1][2][3]" in out


def test_ensure_citations_leaves_marked_answers_alone():
    out = ensure_citations("Setting time is 30 minutes [2].", 3)
    assert out == "Setting time is 30 minutes [2]."


# ---------------------------------------------------------------------------
# Fallback provider transparency in offline MODE B
# ---------------------------------------------------------------------------

def test_fallback_provider_is_transparent_for_general_questions():
    from app.rag.llm import FallbackLLMProvider

    prompt = (
        "RETRIEVED CONTEXT (numbered blocks; cite as [n]):\n\n"
        "[1] Source: IS 1234:2020 | Page 3\n"
        "The final setting time shall not be more than 600 minutes.\n\n"
        "USER QUESTION: What is the capital of France?\n\n"
        "Answer the question."
    )
    answer = FallbackLLMProvider().generate(prompt)
    assert answer.startswith(GENERAL_MARKER)
    assert "GEMINI_API_KEY" in answer


def test_fallback_provider_still_refuses_unsupported_bis_questions():
    from app.rag.llm import FallbackLLMProvider

    prompt = (
        "RETRIEVED CONTEXT (numbered blocks; cite as [n]):\n\n"
        "[1] Source: IS 1234:2020 | Page 3\n"
        "The final setting time shall not be more than 600 minutes.\n\n"
        "USER QUESTION: What is the beryllium content limit requirement in brass fittings?\n\n"
        "Answer the question."
    )
    answer = FallbackLLMProvider().generate(prompt)
    assert "couldn't find sufficient evidence" in answer.lower()
    assert "Try searching the BIS Knowledge Base" in answer
