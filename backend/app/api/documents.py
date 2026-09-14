"""Document management endpoints (admin) + public document search/detail."""
from __future__ import annotations

from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import BASE_DIR, settings
from app.database.base import get_db
from app.dependencies import get_current_user, require_admin
from app.ingestion.service import IngestionError, generate_stored_name, ingest_document, validate_pdf
from app.logging_config import get_logger
from app.models import Document, DocumentChunk, User
from app.schemas.documents import DocumentDetailOut, DocumentOut, StatusResponse

logger = get_logger("app.api.documents")
router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentDetailOut, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    standard_number: str = Form(""),
    title: str = Form(""),
    year: int | None = Form(None),
    document_type: str = Form("standard"),
    category: str = Form("general"),
    description: str = Form(""),
    source_url: str = Form(""),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Upload a PDF and start the ingestion pipeline (extract→chunk→embed→index)."""
    content = await file.read()
    try:
        validate_pdf(file.filename or "upload.pdf", content)
    except IngestionError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    stored_name = generate_stored_name(file.filename or "document.pdf")
    uploads_dir = settings.uploads_path
    dest = uploads_dir / stored_name
    dest.write_bytes(content)

    document = Document(
        name=file.filename or stored_name,
        standard_number=standard_number.strip(),
        title=title.strip() or (file.filename or "").rsplit(".", 1)[0],
        year=year,
        document_type=document_type.strip() or "standard",
        category=category.strip() or "general",
        description=description.strip(),
        file_path=str(dest),
        file_size=len(content),
        source_url=source_url.strip(),
        status="uploaded",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        document = ingest_document(db, document.id)
    except IngestionError as exc:
        logger.warning("Ingestion failed for doc=%s: %s", document.id, exc)
        db.refresh(document)

    return _detail(db, document)


def _detail(db: Session, document: Document) -> DocumentDetailOut:
    out = DocumentDetailOut.model_validate(document)
    out.chunk_count = (
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).count()
    )
    return out


@router.get("", response_model=list[DocumentDetailOut])
def list_documents(
    q: str | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    query = db.query(Document)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Document.name.ilike(like))
            | (Document.title.ilike(like))
            | (Document.standard_number.ilike(like))
        )
    if status_filter:
        query = query.filter(Document.status == status_filter)
    docs = query.order_by(Document.created_at.desc()).all()
    return [_detail(db, d) for d in docs]


@router.get("/{document_id}", response_model=DocumentDetailOut)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return _detail(db, document)


@router.get("/{document_id}/file")
def get_document_file(
    document_id: int,
    page: int | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Serve the stored PDF (path-safe: id-based lookup, no user paths)."""
    document = db.get(Document, document_id)
    if not document or not document.file_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document file not found")
    path = Path(document.file_path)
    if not path.is_absolute():
        path = BASE_DIR / path
    # Path traversal guard: resolved path must live inside uploads dir
    uploads_resolved = settings.uploads_path.resolve()
    if not path.resolve().is_relative_to(uploads_resolved):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid file path")
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File missing on disk")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=document.name,
        headers={"Content-Disposition": f'inline; filename="{document.name}"'},
    )


@router.delete("/{document_id}", response_model=StatusResponse)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

    # Remove file from disk
    if document.file_path:
        path = Path(document.file_path)
        if not path.is_absolute():
            path = BASE_DIR / path
        try:
            if path.exists() and path.resolve().is_relative_to(settings.uploads_path.resolve()):
                path.unlink()
        except OSError:
            logger.warning("Could not delete file for doc=%s", document_id)

    db.delete(document)
    db.commit()
    return StatusResponse(ok=True, detail=f"Document {document_id} deleted")


@router.post("/{document_id}/reindex", response_model=DocumentDetailOut)
def reindex_document(
    document_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    try:
        document = ingest_document(db, document.id)
    except IngestionError:
        db.refresh(document)
    return _detail(db, document)
