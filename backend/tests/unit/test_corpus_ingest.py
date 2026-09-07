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


# ---- Regression: the policy corpus must actually ship -------------------------
#
# Neither Dockerfile COPYed knowledge_base/, and seed_kb resolves it at <repo root>/
# knowledge_base = /app in the image. So the deployed container seeded 195 generated
# buying guides + 19 category guides and ZERO policy documents: product questions kept
# working, every returns/warranty/shipping question answered "I don't have that
# information", and the only signal was one logger.warning at startup.

@pytest.fixture
def fresh_db():
    """An isolated database — ingesting the real corpus must not pollute the
    session-scoped test DB that every other test shares."""
    import os
    import tempfile

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.models import Base

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    eng = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(bind=eng)
    db = sessionmaker(bind=eng)()
    try:
        yield db
    finally:
        db.close()
        eng.dispose()
        try:
            os.unlink(path)
        except OSError:
            pass


def test_full_kb_ingest_produces_the_policy_corpus(fresh_db):
    from sqlalchemy import func, select

    from app.models.knowledge import Document
    from app.seed.seed_kb import ingest_knowledge_base

    assert ingest_knowledge_base(fresh_db) > 0

    by_type = dict(fresh_db.execute(
        select(Document.source_type, func.count(Document.id)).group_by(Document.source_type)
    ).all())
    assert by_type.get("policy", 0) >= 5, by_type

    # The documents Rule 4 (policy grounding) in SYSTEM_PROMPT_RETAIL depends on.
    slugs = set(fresh_db.execute(select(Document.slug)).scalars())
    assert {"returns", "refunds", "warranty", "shipping-delivery",
            "price-match", "faq"} <= slugs, sorted(slugs)

    # The readiness probe must recognise every source_type the seed writes, or a missing
    # corpus would still read as healthy.
    from app.main import POLICY_SOURCE_TYPES
    assert set(by_type) <= POLICY_SOURCE_TYPES, set(by_type) - POLICY_SOURCE_TYPES


def test_missing_corpus_fails_the_seed_loudly(fresh_db, monkeypatch, tmp_path):
    from app.seed import seed_kb

    monkeypatch.setattr(seed_kb, "_KB_DIR", tmp_path / "not-shipped")
    with pytest.raises(seed_kb.KnowledgeBaseMissingError, match="Dockerfile"):
        seed_kb.ingest_knowledge_base(fresh_db)


def test_empty_corpus_directory_also_fails(fresh_db, monkeypatch, tmp_path):
    from app.seed import seed_kb

    empty = tmp_path / "knowledge_base"
    empty.mkdir()
    monkeypatch.setattr(seed_kb, "_KB_DIR", empty)
    with pytest.raises(seed_kb.KnowledgeBaseMissingError):
        seed_kb.ingest_knowledge_base(fresh_db)


def test_missing_corpus_can_be_opted_out_of(fresh_db, monkeypatch, tmp_path):
    """Running without policy documents must be a deliberate choice, not a default."""
    from app.core.config import settings
    from app.seed import seed_kb

    monkeypatch.setattr(seed_kb, "_KB_DIR", tmp_path / "not-shipped")
    monkeypatch.setattr(settings, "require_knowledge_base", False)
    assert seed_kb.ingest_knowledge_base(fresh_db) == 0


def test_both_images_ship_the_policy_corpus():
    """Assert on the Dockerfiles themselves. The seed hard-fail above catches a missing
    corpus at container start, which is late and only visible if someone reads the boot
    log; this catches the missing COPY in CI, where the regression actually happened."""
    root = Path(__file__).resolve().parents[3]
    for dockerfile in (root / "Dockerfile", root / "backend" / "Dockerfile"):
        text = dockerfile.read_text(encoding="utf-8")
        assert "COPY knowledge_base/" in text, f"{dockerfile} does not ship knowledge_base/"
