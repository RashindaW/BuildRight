"""Richer category guides (keyless) + PDF ingestion (skipped without pypdf)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.seed.category_guides import generate_category_guides


def test_category_guides_are_rich_and_unique():
    guides = generate_category_guides()
    assert len(guides) >= 15
    slugs = [g["slug"] for g in guides]
    assert len(slugs) == len(set(slugs))
    g = guides[0]
    assert g["text"].startswith("# ") and "## Choosing the right product" in g["text"]
    assert "| Product | Good for | Options |" in g["text"]   # heterogeneous: a table
    assert "## Safety" in g["text"] or "## Care" in g["text"]


def test_pdf_extraction_reads_the_sample_spec_sheet():
    pytest.importorskip("pypdf")
    sample = Path(__file__).resolve().parents[1].parent / "app" / "seed" / "samples" / "cordless-drill-spec.pdf"
    if not sample.exists():
        pytest.skip("sample PDF not built in this env")
    from app.seed.pdf_ingest import extract_pages
    text = " ".join(extract_pages(sample))
    assert "20V" in text and "torque" in text.lower()  # the spec table extracted
