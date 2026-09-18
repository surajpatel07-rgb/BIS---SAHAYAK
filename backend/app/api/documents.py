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
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session
from urllib.parse import quote as urllib_parse_quote

from app.config import BASE_DIR, settings
from app.database.base import get_db
from app.dependencies import get_current_user, get_optional_user, require_admin
from app.ingestion.service import IngestionError, generate_stored_name, ingest_document, validate_pdf
from app.logging_config import get_logger
from app.models import Document, DocumentChunk, User
from app.schemas.documents import DocumentDetailOut, DocumentOut, StatusResponse
from app.security import FILE_TOKEN_TTL_SECONDS, create_file_token, decode_file_token

logger = get_logger("app.api.documents")
router = APIRouter(prefix="/api/documents", tags=["documents"])


def _pdf_content_disposition(filename: str) -> str:
    """RFC 6266/5987-safe Content-Disposition for a PDF.

    Document names contain non-latin-1 characters (em-dashes etc.), which crash
    Starlette's header encoding when put straight into filename="...". Use an
    ASCII fallback plus filename* for the real (UTF-8) name.
    """
    ascii_fallback = (
        filename.encode("ascii", "ignore").decode("ascii").replace('"', "").strip()
        or "document.pdf"
    )
    if not ascii_fallback.lower().endswith(".pdf"):
        ascii_fallback += ".pdf"
    quoted = urllib_parse_quote(filename, safe="")
    return f"inline; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quoted}"


def _source_unavailable_page(title: str, detail: str, status_code: int) -> HTMLResponse:
    """Friendly HTML error for the document file endpoint.

    This endpoint is opened directly in browser tabs by citation links, so a
    plain JSON error would render as a bare API page. Return a small, clearly
    styled page instead (the SPA's own 401-redirect interceptor does not run
    here — that only applies to in-app fetches).
    """
    return HTMLResponse(
        content=f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Source unavailable — BIS Buddy</title>
<style>
  body {{ font-family: system-ui, sans-serif; background: #f8fafc; color: #334155;
         display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }}
  .card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 16px;
          padding: 2.5rem; max-width: 26rem; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
  h1 {{ font-size: 1.15rem; margin: .75rem 0 .5rem; color: #0f172a; }}
  p {{ font-size: .9rem; line-height: 1.5; margin: .25rem 0; }}
  .icon {{ font-size: 2rem; }}
</style></head>
<body><div class="card"><div class="icon">&#128196;</div>
<h1>Source unavailable</h1>
<p><b>{title}</b></p><p>{detail}</p>
<p style="color:#64748b">Return to BIS Buddy and try opening the citation again.</p>
</div></body></html>""",
        status_code=status_code,
    )


@router.post("/upload", response_model=DocumentDetailOut, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    standard_number: str = Form(""),
    title: str = Form(""),
    year: int | None = Form(None),
    document_type: str = Form("standard"),
    category: str = Form("general_bis"),
    subcategory: str = Form(""),
    product_name: str = Form(""),
    language: str = Form("en"),
    description: str = Form(""),
    source_url: str = Form(""),
    source_name: str = Form(""),
    source_type: str = Form("demo"),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Upload a PDF and start the ingestion pipeline (extract→chunk→embed→index)."""
    from app.knowledge.registry import normalize_category

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
        category=normalize_category(category),
        subcategory=subcategory.strip(),
        product_name=product_name.strip(),
        language=language.strip() or "en",
        description=description.strip(),
        file_path=str(dest),
        file_size=len(content),
        source_url=source_url.strip(),
        source_name=source_name.strip(),
        source_type=source_type.strip() or "demo",
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
    token: str | None = None,
    db: Session = Depends(get_db),
    _user: User | None = Depends(get_optional_user),
):
    """Serve the stored PDF inline (Content-Type: application/pdf).

    Authentication accepts EITHER:
      - a Bearer session token (SPA fetches / iframes with header auth), or
      - a short-lived `?token=` query token minted specifically for this
        document id (browser tab navigation via <a href> cannot send headers).

    This is what lets citation links open the real PDF in a new tab while the
    rest of the API stays header-authenticated. Path-safe: id-based lookup,
    resolved path must live inside the uploads directory.
    """
    token_doc_id = decode_file_token(token) if token else None
    if token_doc_id is None and _user is None:
        return _source_unavailable_page(
            "Sign-in required",
            "This source link has expired or is not authorised. Please open the "
            "citation again from BIS Buddy while signed in.",
            status.HTTP_401_UNAUTHORIZED,
        )
    if token_doc_id is not None and token_doc_id != document_id:
        return _source_unavailable_page(
            "Invalid source link",
            "This link was issued for a different document and cannot be used here.",
            status.HTTP_403_FORBIDDEN,
        )

    document = db.get(Document, document_id)
    if not document or not document.file_path:
        return _source_unavailable_page(
            "Document not found",
            "The referenced source is not present in the knowledge base. It may "
            "have been removed by an administrator.",
            status.HTTP_404_NOT_FOUND,
        )
    path = Path(document.file_path)
    if not path.is_absolute():
        path = BASE_DIR / path
    # Path traversal guard: resolved path must live inside uploads dir
    uploads_resolved = settings.uploads_path.resolve()
    if not path.resolve().is_relative_to(uploads_resolved):
        return _source_unavailable_page(
            "Invalid source link", "The document storage path could not be resolved.", 400
        )
    if not path.exists():
        return _source_unavailable_page(
            "File missing on server",
            "The PDF file for this source is no longer available on the server. "
            "Please ask an administrator to re-upload or re-index the document.",
            status.HTTP_404_NOT_FOUND,
        )
    if not path.suffix.lower().endswith(".pdf"):
        return _source_unavailable_page(
            "Unsupported source", "The stored source is not a PDF document.", 415
        )
    return FileResponse(
        path,
        media_type="application/pdf",
        headers={
            "Content-Disposition": _pdf_content_disposition(document.name),
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, max-age=300",
        },
    )


@router.post("/{document_id}/file-token")
def create_document_file_token(
    document_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Mint a short-lived link token for one document (for <a href> navigation)."""
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return {"token": create_file_token(document_id), "expires_in": FILE_TOKEN_TTL_SECONDS}


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
