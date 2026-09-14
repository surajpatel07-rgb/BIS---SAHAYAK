"""PDF text extraction with per-page tracking (PyMuPDF)."""
from __future__ import annotations

from dataclasses import dataclass

import fitz  # PyMuPDF

from app.logging_config import get_logger

logger = get_logger("app.ingestion.pdf")


class PDFExtractionError(Exception):
    pass


@dataclass
class ExtractedPDF:
    text: str
    page_starts: list[tuple[int, int]]  # (char_offset, page_number)
    page_count: int


def extract_pdf(path: str) -> ExtractedPDF:
    """Extract text page by page, recording the char offset where each page begins."""
    try:
        doc = fitz.open(path)
    except Exception as exc:  # noqa: BLE001
        raise PDFExtractionError(f"Could not open PDF: {exc}") from exc

    if doc.page_count == 0:
        doc.close()
        raise PDFExtractionError("PDF has no pages")

    parts: list[str] = []
    page_starts: list[tuple[int, int]] = []
    offset = 0
    for i, page in enumerate(doc):
        page_text = page.get_text("text") or ""
        page_text = page_text.rstrip() + "\n\n"
        page_starts.append((offset, i + 1))
        parts.append(page_text)
        offset += len(page_text)

    full_text = "".join(parts)
    page_count = doc.page_count
    doc.close()

    if not full_text.strip():
        raise PDFExtractionError(
            "No extractable text found. The PDF may be a scanned image "
            "(OCR is not enabled on this deployment)."
        )

    return ExtractedPDF(text=full_text, page_starts=page_starts, page_count=page_count)
