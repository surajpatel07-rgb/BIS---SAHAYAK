"""Chunking module tests."""
from app.rag.chunking import chunk_text, clean_text

SAMPLE = """1. SCOPE

This standard prescribes requirements for the product.

2. REQUIREMENTS

2.1 Fineness — The residue shall not exceed 10 percent.

2.2 Setting time — The initial setting time shall not be less than 30 minutes.

3. MARKING

Each product shall carry the ISI mark."""


def test_clean_text_removes_soft_hyphens():
    assert clean_text("ces\u00adsi\u00adse") == "cessise"
    assert "  " not in clean_text("a  b\t\tc")


def test_chunks_created():
    chunks = chunk_text(SAMPLE)
    assert len(chunks) >= 2
    assert all(c.text.strip() for c in chunks)


def test_page_numbers_track_offsets():
    pages_text = "Page one content.\n\n" * 1 + "Page two content about marking.\n\n"
    chunks = chunk_text(pages_text, page_starts=[(0, 1), (19, 2)])
    assert all(c.page_number in (1, 2) for c in chunks)


def test_section_metadata_present():
    chunks = chunk_text(SAMPLE)
    sections = {c.section for c in chunks}
    assert len(sections) >= 2  # multiple sections detected
    assert any("SCOPE" in s for s in sections)
    assert any("MARKING" in s for s in sections)


def test_overlap_between_consecutive_chunks():
    text = (" ".join(f"sentence {i} about cement testing." for i in range(60)))
    chunks = chunk_text(text, chunk_size=400, chunk_overlap=80)
    if len(chunks) > 1:
        # overlap: the tail words of chunk 1 appear at the start of chunk 2
        tail = chunks[0].text[-60:]
        assert tail.split()[0] in chunks[1].text


def test_respects_config_sizes():
    chunks = chunk_text(SAMPLE, chunk_size=200, chunk_overlap=40)
    # No chunk should vastly exceed the configured size
    for c in chunks:
        assert len(c.text) < 400
