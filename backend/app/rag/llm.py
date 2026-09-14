"""LLM provider abstraction.

Providers:
- GeminiLLMProvider: Google Gemini via google-genai SDK (streaming + JSON mode).
- FallbackLLMProvider: local extractive answerer used when GEMINI_API_KEY is
  not configured. It composes an answer strictly from retrieved chunks so the
  app remains fully functional offline while still never fabricating facts.

Both providers implement `generate(prompt, system, history)` and
`stream_generate(...)` so the chat service can swap them transparently.

HYBRID ANSWER MODES
The assistant runs in hybrid mode: BIS-specific questions are answered from
retrieved RAG context with citations; general questions (or BIS questions the
indexed documents cannot cover) are answered from Gemini's general knowledge,
marked with [GENERAL ANSWER] so the pipeline never attaches document citations
to claims that did not come from documents.
"""
from __future__ import annotations

import re
from collections.abc import Iterator

from app.config import settings
from app.logging_config import get_logger

logger = get_logger("app.rag.llm")

SYSTEM_PROMPT = """You are BIS Buddy, an AI assistant for Indian Standards (IS) and the \
Bureau of Indian Standards (BIS) services, helping industries, manufacturers and consumers.

You operate in HYBRID mode with two answer styles. For every question, decide which style \
applies:

MODE A — BIS-GROUNDED ANSWERS (the question is about BIS/IS standards, certification, \
compliance, testing, procedures, or product safety/quality requirements):
1. Answer ONLY from the RETRIEVED CONTEXT provided in the prompt.
2. NEVER invent standard numbers (IS XXXX), certification requirements, fees, forms, \
deadlines or government rules.
3. NEVER fabricate citations, and never cite a document or page that is not in the \
retrieved context.
4. When you state a factual BIS-related claim, it must come from the context; the calling \
service resolves citation markers from the sources you use.
5. If the retrieved context addresses the topic but lacks the specific detail asked for, \
answer with what IS in the context, then state which specific detail the indexed \
documents do not cover and suggest uploading or consulting the relevant standard.
6. Adapt tone to the user's mode: CONSUMER = simple language, safety focus, how to check \
the ISI mark; INDUSTRY = precise, procedure/compliance-oriented language.

MODE B — GENERAL-KNOWLEDGE ANSWERS (everyday/general questions, or BIS-adjacent questions \
where the retrieved context is unrelated to the question and clearly insufficient):
1. Do NOT refuse and do NOT reply with "I could not find sufficient information" — \
answer the question normally from your general knowledge in a helpful, polite, \
professional tone.
2. Stay transparent: briefly note that the answer draws on general knowledge rather \
than the indexed BIS documents (one short lead-in line is enough).
3. Never present general-knowledge claims as if they came from BIS documents, and never \
invent standard numbers, fees, forms or rules. Where BIS involvement genuinely applies, \
point the user to official channels (e.g. the BIS website / manakonline) without \
inventing specific requirements.

DECIDING BETWEEN MODES:
- BIS-specific question + relevant retrieved context -> MODE A with [n] citations.
- BIS-specific question + unrelated or insufficient retrieved context -> MODE B, noting \
that the indexed documents do not yet cover the topic.
- General, everyday question -> MODE B regardless of what was retrieved.

OUTPUT FORMAT:
- Answer directly, in clear prose and short bullets. Keep the answer under 350 words \
unless asked for detail.
- MODE A only: immediately after any sentence(s) that rely on a specific retrieved chunk, \
append its citation marker in square brackets, e.g. [1] or [2][3]. Every MODE A answer \
MUST include at least one [n] citation marker — an answer stating BIS facts with zero \
[n] markers is a failure.
- MODE B only: begin the reply with the exact line [GENERAL ANSWER] on its own, then the \
answer. Never append [n] markers, because no retrieved document is being quoted."""


class LLMError(Exception):
    """Raised when the LLM provider fails."""


REFUSAL_PHRASE = "could not find sufficient information"

# Marker emitted by the LLM for MODE B (general-knowledge) answers in hybrid mode.
# The chat pipeline strips it before saving/streaming and skips citation resolution
# for such answers, so general answers never display document citations.
GENERAL_MARKER = "[GENERAL ANSWER]"


def ensure_citations(answer: str, n_chunks: int) -> str:
    """Deterministic safety net: grounded answers always carry citation markers.

    Gemini occasionally ignores the [n] marker instruction for MODE A answers.
    The answer was still generated from the retrieved context blocks, so when
    markers are missing we append a Sources line referencing the top chunks.
    Refusals and [GENERAL ANSWER] (MODE B) replies are left untouched: a general
    answer must never be decorated with document citations it did not use.
    """
    import re

    lowered = answer.lower()
    if (
        n_chunks <= 0
        or REFUSAL_PHRASE in lowered
        or GENERAL_MARKER.lower() in lowered
    ):
        return answer
    if re.search(r"\[\d{1,2}\]", answer):
        return answer
    top = "".join(f"[{i}]" for i in range(1, min(3, n_chunks) + 1))
    logger.info("Answer had no citation markers; appended Sources %s", top)
    return answer.rstrip() + f"\n\nSources: {top}"


class BaseLLMProvider:
    name = "base"

    def generate(self, prompt: str, system: str = "", history: list[dict] | None = None) -> str:
        raise NotImplementedError

    def stream_generate(
        self, prompt: str, system: str = "", history: list[dict] | None = None
    ) -> Iterator[str]:
        raise NotImplementedError


class GeminiLLMProvider(BaseLLMProvider):
    name = "gemini"

    def __init__(self) -> None:
        from google import genai

        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY not configured")
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_model

    def _contents(self, prompt: str, history: list[dict] | None):
        contents: list[dict] = []
        for m in history or []:
            role = "user" if m.get("role") == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m.get("content", "")}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})
        return contents

    def generate(self, prompt: str, system: str = "", history: list[dict] | None = None) -> str:
        try:
            resp = self._client.models.generate_content(
                model=self._model,
                contents=self._contents(prompt, history),
                config={
                    "system_instruction": system or SYSTEM_PROMPT,
                    "temperature": 0.2,
                    "max_output_tokens": settings.gemini_max_output_tokens,
                },
            )
            text = getattr(resp, "text", None)
            if not text:
                raise LLMError("Gemini returned an empty response")
            return text
        except LLMError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error("Gemini generate failed: %s", exc)
            raise LLMError(f"Gemini API error: {exc}") from exc

    def stream_generate(
        self, prompt: str, system: str = "", history: list[dict] | None = None
    ) -> Iterator[str]:
        try:
            stream = self._client.models.generate_content_stream(
                model=self._model,
                contents=self._contents(prompt, history),
                config={
                    "system_instruction": system or SYSTEM_PROMPT,
                    "temperature": 0.2,
                    "max_output_tokens": settings.gemini_max_output_tokens,
                },
            )
            for chunk in stream:
                piece = getattr(chunk, "text", None)
                if piece:
                    yield piece
        except Exception as exc:  # noqa: BLE001
            logger.error("Gemini stream failed: %s", exc)
            raise LLMError(f"Gemini streaming error: {exc}") from exc


class FallbackLLMProvider(BaseLLMProvider):
    """Deterministic extractive answerer (offline dev mode).

    Composes an answer exclusively from the numbered context blocks so behaviour
    matches the grounded contract even without an API key. Produces:
      - a lead-in sentence, the most relevant sentences from top chunks with
        citation markers, and a sources hint.
    """

    name = "fallback"

    def generate(self, prompt: str, system: str = "", history: list[dict] | None = None) -> str:
        return self._compose(prompt)

    def stream_generate(self, prompt: str, system: str = "", history: list[dict] | None = None):
        text = self._compose(prompt)
        for token in text.split(" "):
            yield token + " "

    # ------------------------------------------------------------------
    def _compose(self, prompt: str) -> str:
        qm = re.search(r"USER QUESTION:\s*(.+)", prompt)
        question = qm.group(1).strip() if qm else ""

        blocks = re.findall(
            r"\[(\d+)\][^\n]*\n(.*?)(?=\n\[\d+\]|\nUSER QUESTION:|\Z)",
            prompt,
            flags=re.DOTALL,
        )
        if detect_answer_mode(question) == "general":
            # MODE B without an API key: be transparent that generative
            # general-knowledge answers are unavailable offline rather than
            # pretending a refusal is the answer to the user's question.
            return (
                GENERAL_MARKER
                + " Offline development mode can only answer from the indexed BIS "
                "documents. Configure GEMINI_API_KEY to enable full general-knowledge "
                "answers."
            )
        if not blocks:
            return (
                "I could not find sufficient information in the indexed BIS documents "
                "to answer this reliably. Please try rephrasing, or ask an administrator "
                "to index the relevant standard."
            )

        # Rank sentences from each block by query-term overlap
        q_tokens = set(re.findall(r"[a-z0-9]+", question.lower())) - {
            "what", "which", "how", "the", "a", "an", "is", "are", "for", "of", "to",
            "and", "in", "on", "does", "do", "i", "my", "me", "should", "can",
        }

        max_markers = int(getattr(self, "_max_markers", 4))
        picked: list[tuple[int, str]] = []
        best_sentence_overlap = 0  # distinct query terms in the single best sentence
        for marker, body in blocks[:max_markers]:
            # Drop the "Source: ... | Page n" header line of each context block
            body_lines = [ln for ln in body.strip().splitlines() if not ln.strip().startswith("Source:")]
            body = "\n".join(body_lines).strip()
            sentences = re.split(r"(?<=[.!?])\s+", body)
            scored = []
            for s in sentences:
                st = set(re.findall(r"[a-z0-9]+", s.lower()))
                if q_tokens:
                    overlap = len(q_tokens & st)
                    if overlap == 0:
                        continue  # only use sentences that actually match the question
                else:
                    overlap = len(st) * 0.1
                scored.append((overlap, s, st))
            scored.sort(key=lambda t: t[0], reverse=True)
            if scored:
                best_sentence_overlap = max(best_sentence_overlap, scored[0][0])
            for _, s, _st in scored[:2]:
                if len(s) > 40 and not s.startswith(("http", "Page")):
                    picked.append((int(marker), s))

        # Minimum-evidence gate: for multi-token questions the single best
        # sentence must share at least TWO distinct query terms. This stops
        # generic word collisions ("requirement", "content", "standard" in
        # different sentences) from producing a confident-looking extractive
        # answer to an unrelated question, while real topical matches share
        # several terms (e.g. "packaged", "drinking", "water").
        if not picked or (
            q_tokens and len(q_tokens) >= 2 and best_sentence_overlap < 2
        ):
            return (
                "I could not find sufficient information in the indexed BIS documents "
                "to answer this reliably."
            )

        lines = [f"- {s} [{m}]" for m, s in picked[:6]]
        header = (
            "Based on the indexed BIS documents (development mode: extractive answer, "
            "configure GEMINI_API_KEY for full generative answers):"
        )
        return header + "\n" + "\n".join(lines)


def get_llm_provider() -> BaseLLMProvider:
    if settings.llm_available:
        try:
            return GeminiLLMProvider()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Gemini provider unavailable (%s); using fallback", exc)
    return FallbackLLMProvider()


# ----------------------------------------------------------------------------
# Hybrid answer-mode classification
#
# BIS-oriented questions are answered from RAG context (MODE A). Everything
# else — everyday questions, greetings, or BIS questions the indexed corpus
# cannot cover — falls through to Gemini's general knowledge (MODE B) instead
# of being refused. The classifier is deliberately lightweight and
# recall-oriented: uncertain queries are treated as BIS-oriented so the model
# still sees the retrieved context, and it may use MODE B transparently when
# the context turns out to be unrelated.
# ----------------------------------------------------------------------------

_BIS_TOPIC_TERMS = (
    # standards & documents
    "is", "bis", "isi", "standard", "standards", "specification", "code",
    "annex", "clause", "guideline", "guidelines", "manual", "act", "rules",
    "bureau", "manak",
    # certification & compliance
    "certif", "licence", "license", "mark", "compliance", "conform",
    "register", "registration", "approval", "accredit", "audit",
    # industry procedure
    "manufactur", "testing", "test", "requirement", "requirements", "procedure",
    "documentation", "quality", "specification", "technical", "regulation",
    "factory", "production", "import", "export", "safety", "hazard",
    # consumer-side BIS topics
    "complaint", "grievance", "hallmark", "label", "warranty", "genuine",
    "fake", "counterfeit", "verify", "authentic", "recall",
)

_NON_BIS_HINTS = (
    "weather", "recipe", "joke", "poem", "movie", "song", "cricket score",
    "capital of", "who is the president", "translate", "python code",
    "write an email", "resume",
)


def detect_answer_mode(question: str) -> str:
    """Classify a question as "bis" (grounded) or "general" (model knowledge).

    Recall-oriented: anything plausibly BIS-related is treated as "bis" so the
    retrieved context stays available to the model. Truly general questions
    (or those with no topic terms at all) route to "general".
    """
    q = (question or "").lower()
    if not q.strip():
        return "general"
    if any(h in q for h in _NON_BIS_HINTS):
        return "general"
    # "is" is only a BIS signal as a standard prefix ("is 1234", "is 3025");
    # as a bare word it is the verb "is", so require a following number of at
    # least two digits (real IS standard numbers).
    tokens = re.findall(r"[a-z0-9]+", q)
    for i, tok in enumerate(tokens):
        if tok == "is" and i + 1 < len(tokens) and len(tokens[i + 1]) >= 2 and tokens[i + 1].isdigit():
            return "bis"
    for term in _BIS_TOPIC_TERMS:
        if term != "is" and term in q:
            return "bis"
    return "general"
