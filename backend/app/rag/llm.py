"""LLM provider abstraction.

Providers:
- GeminiLLMProvider: Google Gemini via google-genai SDK (streaming + JSON mode).
- FallbackLLMProvider: local extractive answerer used when GEMINI_API_KEY is
  not configured. It composes an answer strictly from retrieved chunks so the
  app remains fully functional offline while still never fabricating facts.

Both providers implement `generate(prompt, system, history)` and
`stream_generate(...)` so the chat service can swap them transparently.
"""
from __future__ import annotations

from collections.abc import Iterator

from app.config import settings
from app.logging_config import get_logger

logger = get_logger("app.rag.llm")

SYSTEM_PROMPT = """You are BIS Buddy, an AI assistant for Indian Standards (IS) and the \
Bureau of Indian Standards (BIS) services, helping industries, manufacturers and consumers.

STRICT GROUNDING RULES (non-negotiable):
1. Answer ONLY from the RETRIEVED CONTEXT provided in the prompt.
2. If the retrieved context does not contain enough information to answer reliably, say \
exactly: "I could not find sufficient information in the indexed BIS documents to answer \
this reliably." and suggest what the user could ask instead or upload.
3. NEVER invent standard numbers (IS XXXX), certification requirements, fees, forms, \
deadlines or government rules.
4. NEVER fabricate citations, and never cite a document or page that is not in the \
retrieved context.
5. When you state a factual BIS-related claim, it must come from the context; the calling \
service attaches citation markers automatically from the sources you use.
6. You may give general, clearly-labelled explanations (e.g. what a conformity assessment \
is) but must distinguish them from retrieved facts.
7. Adapt tone to the user's mode: CONSUMER mode = simple language, safety focus, how to \
check the ISI mark; INDUSTRY mode = precise, procedure/compliance-oriented language.

OUTPUT FORMAT:
- Answer the question directly, in clear prose and short bullets.
- Immediately after any sentence(s) that rely on a specific retrieved chunk, append its \
citation marker in square brackets, e.g. [1] or [2][3]. Markers refer to the numbered \
context blocks in the prompt.
- MANDATORY: every non-refusal answer MUST include at least one [n] citation marker. \
An answer stating BIS facts with zero [n] markers is a failure — cite the block(s) you \
used, e.g. end the first fact sentence with [1].
- Keep the answer under 350 words unless asked for detail."""


class LLMError(Exception):
    """Raised when the LLM provider fails."""


REFUSAL_PHRASE = "could not find sufficient information"


def ensure_citations(answer: str, n_chunks: int) -> str:
    """Deterministic safety net: non-refusal answers always carry citation markers.

    Gemini occasionally ignores the [n] marker instruction. The answer was still
    generated from the retrieved context blocks, so when markers are missing we
    append a Sources line referencing the top chunks. This keeps the citation
    contract intact (every factual answer shows where it came from) without the
    LLM inventing anything — markers only ever reference real retrieved chunks.
    """
    import re

    if n_chunks <= 0 or REFUSAL_PHRASE in answer.lower():
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
        import re

        blocks = re.findall(
            r"\[(\d+)\][^\n]*\n(.*?)(?=\n\[\d+\]|\nUSER QUESTION:|\Z)",
            prompt,
            flags=re.DOTALL,
        )
        if not blocks:
            return (
                "I could not find sufficient information in the indexed BIS documents "
                "to answer this reliably. Please try rephrasing, or ask an administrator "
                "to index the relevant standard."
            )

        # Rank sentences from each block by query-term overlap
        qm = re.search(r"USER QUESTION:\s*(.+)", prompt)
        question = qm.group(1).strip() if qm else ""
        q_tokens = set(re.findall(r"[a-z0-9]+", question.lower())) - {
            "what", "which", "how", "the", "a", "an", "is", "are", "for", "of", "to",
            "and", "in", "on", "does", "do", "i", "my", "me", "should", "can",
        }

        max_markers = int(getattr(self, "_max_markers", 4))
        picked: list[tuple[int, str]] = []
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
                scored.append((overlap, s))
            scored.sort(key=lambda t: t[0], reverse=True)
            for _, s in scored[:2]:
                if len(s) > 40 and not s.startswith(("http", "Page")):
                    picked.append((int(marker), s))

        if not picked:
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
