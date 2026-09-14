"""Chat endpoints: grounded RAG chat with citations, streaming variant, and
conversation management."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database.base import get_db
from app.dependencies import get_current_user
from app.logging_config import get_logger
from app.models import Conversation, Message, User
from app.models.models import utcnow
from app.rag.llm import (
    FallbackLLMProvider,
    GENERAL_MARKER,
    LLMError,
    detect_answer_mode,
    ensure_citations,
    get_llm_provider,
)
from app.rag.retrieval import RetrievalService, build_history, build_prompt
from app.rag.vector_store import RetrievedChunk
from app.schemas.chat import ChatRequest, ChatResponse, CitationSchema
from app.schemas.documents import ConversationDetail, ConversationSummary

logger = get_logger("app.api.chat")
router = APIRouter(prefix="/api", tags=["chat"])

# Exported for tests: extractive fallback is exercised without network
__all__ = ["router", "chat", "stream_chat"]


def _citations(chunks: list[RetrievedChunk]) -> list[CitationSchema]:
    return [CitationSchema(**c.to_citation()) for c in chunks]


def _save_messages(
    db: Session,
    conversation: Conversation,
    user_text: str,
    answer: str,
    citations: list[CitationSchema],
) -> tuple[Message, Message]:
    user_msg = Message(
        conversation_id=conversation.id, role="user", content=user_text, sources_json=None
    )
    db.add(user_msg)
    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer,
        sources_json={"sources": [c.model_dump() for c in citations]},
    )
    db.add(assistant_msg)
    conversation.updated_at = utcnow()
    db.commit()
    db.refresh(user_msg)
    db.refresh(assistant_msg)
    return user_msg, assistant_msg


def _title_for(text: str) -> str:
    text = " ".join(text.split())
    return text[:80] + ("…" if len(text) > 80 else "")


def _hybridize(
    question: str,
    answer: str,
    chunks: list[RetrievedChunk],
    force_general: bool = False,
) -> tuple[str, list[RetrievedChunk]]:
    """Hybrid post-processing shared by /chat and /chat/stream.

    detect_answer_mode routes the question: "bis" questions are grounded in the
    retrieved chunks (citations guaranteed via ensure_citations), while
    "general" questions are answered from the model's general knowledge. For
    general answers the [GENERAL ANSWER] marker is stripped from the visible
    text and no document citations are attached, so the UI never shows a
    "Source: <pdf>" card for an answer that did not use the documents.
    force_general marks answers where the model itself signalled MODE B (the
    [GENERAL ANSWER] marker was present) even though the question classified
    as BIS — e.g. the indexed context turned out to be unrelated.
    """
    if not force_general and detect_answer_mode(question) != "general":
        # MODE A: grounded answer — guarantee citation markers, then resolve
        # the [n] markers to only the chunks actually cited.
        answer = ensure_citations(answer, len(chunks))
        cited = _extract_cited_markers(answer, len(chunks))
        used = [chunks[i - 1] for i in cited if 0 <= i - 1 < len(chunks)]
        return answer, used
    # MODE B: general-knowledge answer — strip the internal marker and drop citations.
    cleaned = answer.replace(GENERAL_MARKER, "").strip()
    return cleaned, []


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Grounded RAG chat: retrieve → rerank → LLM → answer + citations."""
    try:
        # 1) Get or create conversation
        if payload.conversation_id:
            conversation = db.get(Conversation, payload.conversation_id)
            if not conversation or conversation.user_id != current_user.id:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
        else:
            conversation = Conversation(user_id=current_user.id, mode=payload.mode)
            db.add(conversation)
            db.flush()

        # 2) History for conversational context (excluding nothing; last 8 msgs)
        history_rows = (
            db.query(Message)
            .filter(Message.conversation_id == conversation.id)
            .order_by(Message.id)
            .all()
        )
        history = build_history(
            [{"role": m.role, "content": m.content} for m in history_rows]
        )

        # 3) Retrieval (query = raw user message; metadata filter = user's docs)
        retrieval = RetrievalService()
        chunks = retrieval.retrieve(db, payload.message)

        # 4) Grounded prompt
        prompt = build_prompt(payload.message, payload.mode, history, chunks)

        # 5) LLM
        provider = get_llm_provider()
        try:
            answer = provider.generate(prompt, history=history)
        except LLMError as exc:
            logger.error("LLM generation failed: %s", exc)
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                "The AI service is temporarily unavailable. Please try again shortly.",
            ) from exc
        # 6) Hybrid post-processing: grounded vs general answers + citations
        used_general = GENERAL_MARKER in answer
        answer, used = _hybridize(
            payload.message, answer, chunks, force_general=used_general
        )
        citations = _citations(used)

        # 7) Persist
        if not conversation.messages:
            conversation.title = _title_for(payload.message)
        user_msg, assistant_msg = _save_messages(
            db, conversation, payload.message, answer, citations
        )

        return ChatResponse(
            conversation_id=conversation.id,
            message_id=assistant_msg.id,
            answer=answer,
            sources=citations,
            mode=payload.mode,
            llm_provider=provider.name,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Chat failed unexpectedly")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Something went wrong while processing your question.",
        ) from exc


@router.post("/chat/stream")
def stream_chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SSE streaming variant of /chat. Streams answer text; a final JSON event
    carries conversation/message ids and the citations used."""
    try:
        if payload.conversation_id:
            conversation = db.get(Conversation, payload.conversation_id)
            if not conversation or conversation.user_id != current_user.id:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
        else:
            conversation = Conversation(user_id=current_user.id, mode=payload.mode)
            db.add(conversation)
            db.flush()

        history_rows = (
            db.query(Message)
            .filter(Message.conversation_id == conversation.id)
            .order_by(Message.id)
            .with_entities(Message.role, Message.content, Message.id)
            .all()
        )
        history = build_history(
            [{"role": r[0], "content": r[1]} for r in history_rows]
        )

        chunks = RetrievalService().retrieve(db, payload.message)
        prompt = build_prompt(payload.message, payload.mode, history, chunks)

        provider = get_llm_provider()
    except HTTPException:
        raise
    except Exception:
        logger.exception("Stream setup failed")
        raise HTTPException(500, "Could not start streaming response") from None

    def event_stream():
        answer_parts: list[str] = []
        try:
            yield sse("meta", {
                "conversation_id": conversation.id,
                "mode": payload.mode,
                "llm_provider": provider.name,
                "retrieved": len(chunks),
            })
            marker_filter = _MarkerFilter(
                provider.stream_generate(prompt, history=history)
            )
            try:
                for piece in marker_filter:
                    answer_parts.append(piece)
                    yield sse("delta", {"text": piece})
            except LLMError as exc:
                logger.error("LLM streaming failed: %s", exc)
                yield sse("error", {"message": "The AI service is temporarily unavailable."})
                return

            answer = "".join(answer_parts)
            answer, used = _hybridize(
                payload.message,
                answer,
                chunks,
                force_general=marker_filter.marker_seen,
            )
            citations = _citations(used)

            if not conversation.messages:
                conversation.title = _title_for(payload.message)
            user_msg, assistant_msg = _save_messages(
                db, conversation, payload.message, answer, citations
            )
            yield sse("done", {
                "conversation_id": conversation.id,
                "message_id": assistant_msg.id,
                "sources": [c.model_dump() for c in citations],
            })
        except Exception:  # noqa: BLE001
            logger.exception("Streaming failed mid-flight")
            try:
                yield sse("error", {"message": "Streaming interrupted."})
            except Exception:  # noqa: BLE001
                pass

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


class _MarkerFilter:
    """Filter a token stream, removing a leading [GENERAL ANSWER] marker.

    The marker may be split across streamed pieces, so the head is buffered
    until it either matches the marker prefix (then the marker is swallowed)
    or diverges from it (then everything is released untouched). ``marker_seen``
    records whether the marker was detected, so callers can treat the answer
    as MODE B (general) after streaming completes.
    """

    def __init__(self, pieces) -> None:
        self._pieces = pieces
        self.marker_seen = False

    def __iter__(self):
        return self._gen()

    def _gen(self):
        marker = GENERAL_MARKER
        head = ""
        decided = False
        for piece in self._pieces:
            if decided:
                yield piece
                continue
            head += piece
            stripped = head.lstrip()
            if not stripped.startswith(marker[: min(len(stripped), len(marker))]):
                decided = True
                yield head
                continue
            if len(stripped) > len(marker):
                decided = True
                self.marker_seen = True
                rest = stripped[len(marker):].lstrip("\n :")
                if rest:
                    yield rest
        if not decided and head:
            stripped = head.lstrip()
            if stripped.startswith(marker):
                self.marker_seen = True
                rest = stripped[len(marker):].lstrip("\n :")
                if rest:
                    yield rest
            else:
                yield head


def _extract_cited_markers(answer: str, available: int) -> list[int]:
    """Find [n] markers in the answer, in first-appearance order."""
    import re

    seen: list[int] = []
    for m in re.finditer(r"\[(\d{1,2})\]", answer):
        n = int(m.group(1))
        if 1 <= n <= available and n not in seen:
            seen.append(n)
    return seen


# ----------------------------------------------------------------------------
# Conversation management
# ----------------------------------------------------------------------------
from fastapi import Body  # noqa: E402


@router.get("/conversations")
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    q: str | None = None,
):
    """List the user's conversations, newest first, with search."""
    query = db.query(Conversation).filter(Conversation.user_id == current_user.id)
    if q:
        like = f"%{q}%"
        query = query.filter(Conversation.title.ilike(like))
    convs = query.order_by(Conversation.updated_at.desc()).limit(100).all()
    return [ConversationSummary.model_validate(c).model_dump() for c in convs]


@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv = db.get(Conversation, conversation_id)
    if not conv or conv.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    detail = ConversationDetail.model_validate(conv)
    return detail.model_dump()


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv = db.get(Conversation, conversation_id)
    if not conv or conv.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    db.delete(conv)
    db.commit()
    return {"ok": True}
