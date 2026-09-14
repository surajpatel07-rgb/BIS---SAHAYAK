"""Configurable, section-aware text chunking.

Strategy:
1. Split cleaned text into sections using heading patterns (e.g. "5.2 ...").
2. Pack paragraphs into chunks up to CHUNK_SIZE chars with CHUNK_OVERLAP chars
   of carried-over text between consecutive chunks.
3. Track approximate page numbers using a page-start offset index.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.config import settings
from app.logging_config import get_logger

logger = get_logger("app.rag.chunking")

# Matches heading LINES like "5.2 Fineness", "APPENDIX A", "SECTION 4", "4. REQUIREMENTS"
_HEADING_RE = re.compile(
    r"^[ \t]*(?:"
    r"\d+(?:\.\d+){0,3}\.?[ \t]+\S[^\n]{0,110}"   # 5.2 Some heading text
    r"|APPENDIX[ \t]+[A-Z0-9]+[^\n]{0,80}"          # APPENDIX A ...
    r"|ANNEX[ \t]+[A-Z0-9]+[^\n]{0,80}"             # ANNEX B ...
    r"|(?:SECTION|CLAUSE)[ \t]+\d+[^\n]{0,80}"      # SECTION 4 ...
    r"|[A-Z][A-Z \-/&,()']{5,109}"                  # ALL CAPS HEADING
    r")[ \t]*$",
    re.MULTILINE,
)

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")


@dataclass
class Chunk:
    text: str
    page_number: int
    section: str = ""
    metadata: dict = field(default_factory=dict)


def _char_to_page(offset: int, page_starts: list[tuple[int, int]]) -> int:
    """Map a character offset to a 1-based page number.

    page_starts: sorted list of (start_offset, page_number).
    """
    page = page_starts[0][1]
    for start, num in page_starts:
        if start <= offset:
            page = num
        else:
            break
    return page


def _split_sentences(text: str) -> list[str]:
    parts = _SENTENCE_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


def clean_text(text: str) -> str:
    """Normalize whitespace and remove extraction artifacts."""
    text = text.replace("\u00ad", "")  # soft hyphen
    text = re.sub(r"-\n(?=[a-z])", "", text)  # de-hyphenate line breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(
    text: str,
    page_starts: list[tuple[int, int]] | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Chunk]:
    """Split cleaned text into overlapping, section-aware chunks."""
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap
    page_starts = page_starts or [(0, 1)]

    # 1) Detect section boundaries
    sections: list[tuple[int, str]] = []  # (start_offset, section_title)
    for m in _HEADING_RE.finditer(text):
        sections.append((m.start(), m.group(0).strip()))

    # 2) Build section ranges
    ranges: list[tuple[int, int, str]] = []
    for i, (start, title) in enumerate(sections):
        end = sections[i + 1][0] if i + 1 < len(sections) else len(text)
        if end - start > 40:  # skip tiny fragments
            ranges.append((start, end, title))
    if not ranges:
        ranges = [(0, len(text), "")]

    chunks: list[Chunk] = []
    seq = 0

    for start, end, title in ranges:
        section_text = text[start:end].strip()
        if not section_text:
            continue

        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", section_text) if p.strip()]
        current: list[str] = []
        current_len = 0

        def flush() -> None:
            nonlocal seq, current, current_len
            body = "\n\n".join(current).strip()
            if not body:
                return
            if len(body) < 30:
                # too small alone; will usually get absorbed by overlap
                pass
            page = _char_to_page(start, page_starts)
            chunks.append(
                Chunk(
                    text=body,
                    page_number=page,
                    section=title[:300],
                    metadata={"sequence": seq},
                )
            )
            seq += 1
            if chunk_overlap > 0 and len(body) > chunk_overlap:
                tail = body[-chunk_overlap:]
                # start tail at a word boundary
                sp = tail.find(" ")
                if sp != -1:
                    tail = tail[sp + 1 :]
                current = [tail]
                current_len = len(tail)
            else:
                current = []
                current_len = 0

        for para in paragraphs:
            if len(para) > chunk_size:
                # Split long paragraphs by sentence
                sentences = _split_sentences(para)
                for sent in sentences:
                    if current_len + len(sent) + 1 > chunk_size and current:
                        flush()
                    current.append(sent)
                    current_len += len(sent) + 1
            else:
                if current_len + len(para) + 2 > chunk_size and current:
                    flush()
                current.append(para)
                current_len += len(para) + 2

        if current:
            flush()

    return chunks
