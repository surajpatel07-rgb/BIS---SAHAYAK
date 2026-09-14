"""Feedback, admin stats, and health endpoints."""
from sqlalchemy import text as sa_text

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database.base import get_db
from app.dependencies import get_current_user, require_admin
from app.models import Conversation, Document, DocumentChunk, Feedback, Message, User
from app.rag.embeddings import get_embedding_provider
from app.schemas.documents import AdminStats, FeedbackOut, FeedbackRequest, StatusResponse

router = APIRouter(tags=["misc"])


@router.post("/api/feedback", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    payload: FeedbackRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    message = db.get(Message, payload.message_id)
    if not message:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Message not found")

    existing = (
        db.query(Feedback).filter(Feedback.message_id == payload.message_id).first()
    )
    if existing:
        existing.rating = payload.rating
        existing.comment = payload.comment
    else:
        feedback = Feedback(
            message_id=payload.message_id, rating=payload.rating, comment=payload.comment
        )
        db.add(feedback)
    db.commit()
    fb = db.query(Feedback).filter(Feedback.message_id == payload.message_id).first()
    return FeedbackOut.model_validate(fb)


@router.get("/api/admin/stats", response_model=AdminStats)
def admin_stats(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return AdminStats(
        total_documents=db.query(func.count(Document.id)).scalar() or 0,
        indexed_documents=db.query(func.count(Document.id)).filter(Document.status == "indexed").scalar() or 0,
        processing_documents=db.query(func.count(Document.id)).filter(
            Document.status.in_(["uploaded", "processing", "extracting", "chunking", "embedding"])
        ).scalar() or 0,
        failed_documents=db.query(func.count(Document.id)).filter(Document.status == "failed").scalar() or 0,
        total_chunks=db.query(func.count(DocumentChunk.id)).scalar() or 0,
        total_conversations=db.query(func.count(Conversation.id)).scalar() or 0,
        total_messages=db.query(func.count(Message.id)).scalar() or 0,
        total_users=db.query(func.count(User.id)).scalar() or 0,
        llm_provider=("gemini" if settings.llm_available else "fallback (no API key)"),
        embedding_provider=settings.embedding_provider,
    )


@router.get("/api/admin/feedback", response_model=list[FeedbackOut])
def admin_feedback(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return db.query(Feedback).order_by(Feedback.created_at.desc()).limit(100).all()


@router.get("/health", response_model=StatusResponse)
def health(db: Session = Depends(get_db)):
    """Liveness + DB connectivity check."""
    try:
        db.execute(sa_text("SELECT 1"))
        return StatusResponse(ok=True, detail="healthy")
    except Exception:  # noqa: BLE001
        return StatusResponse(ok=False, detail="database unavailable")


@router.get("/api/config")
def public_config(_user: User = Depends(get_current_user)):
    """Non-sensitive runtime config for the frontend (no keys exposed)."""
    return {
        "llm_provider": "gemini" if settings.llm_available else "fallback",
        "embedding_provider": settings.embedding_provider,
        "voice_supported_note": "Uses browser SpeechRecognition; availability checked client-side.",
    }
