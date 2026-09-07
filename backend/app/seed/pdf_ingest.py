"""PDF / spec-sheet ingestion into the vector knowledge base.

Real retailer corpora are PDFs (manuals, spec sheets, MSDS). This extracts text
page-by-page (pypdf), chunks it through the same pipeline as the markdown KB, and
upserts it as Documents — so a client's PDF library is one `ingest_pdf()` call away.

pypdf/reportlab are OPTIONAL ingestion deps (see requirements-ingest.txt), imported
lazily so the deployed runtime never needs them.

    pip install -r app/seed/requirements-ingest.txt
    python -m app.seed.pdf_ingest          # builds a sample spec sheet + ingests it
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("app.seed.pdf_ingest")

_SAMPLE = Path(__file__).resolve().parent / "samples" / "cordless-drill-spec.pdf"


def embed_pending_chunks(db) -> int:
    """Vectorise any chunk that still has no embedding. Returns the count written.

    Ingestion MUST call this. `_upsert_document` deliberately writes chunks without
    vectors (the seed embeds them in a later pass), so a document added at runtime is
    otherwise invisible to the vector arm — and, before the none_as_null fix, its NULL
    vector poisoned every KB query. Best-effort: a provider outage must not fail the
    ingest, it only leaves the document lexically searchable until the next seed.
    """
    try:
        from app.ai.embeddings.indexer import embed_documents
        from app.ai.embeddings.provider import get_embedding_provider

        return embed_documents(db, get_embedding_provider())
    except Exception:  # noqa: BLE001 - ingestion succeeds; vectors can be backfilled
        logger.exception("ingest: embedding step failed — document is lexical-only for now")
        return 0


def extract_pages(pdf_path: str | Path) -> list[str]:
    """Return the text of each page (pypdf)."""
    from pypdf import PdfReader
    reader = PdfReader(str(pdf_path))
    return [(page.extract_text() or "").strip() for page in reader.pages]


def ingest_pdf(db, pdf_path: str | Path, slug: str, title: str,
               source_type: str = "manual") -> int:
    """Extract a PDF and upsert it as a Document + chunks. Returns chunk count."""
    from app.seed.seed_kb import _upsert_document
    pages = extract_pages(pdf_path)
    text = "\n\n".join(f"## Page {i + 1}\n{t}" for i, t in enumerate(pages) if t)
    n = _upsert_document(db, slug, title, source_type, text, source_path=str(pdf_path))
    db.commit()
    v = embed_pending_chunks(db)
    logger.info("pdf_ingest: %s -> %d chunks (%d vectors)", slug, n, v)
    return n


def ingest_image_manual(db, data: bytes, media_type: str, slug: str, title: str,
                        source_type: str = "manual") -> int:
    """OCR a photographed manual/spec page (Claude vision) → upsert as a Document.

    The image counterpart to ingest_pdf: a customer's snapshot of a paper manual
    becomes vector-searchable KB content. Returns chunk count (0 if OCR yields nothing).
    """
    from app.ai.vision import ocr_image_to_text
    from app.seed.seed_kb import _upsert_document
    text = ocr_image_to_text(data, media_type)
    if not text.strip():
        return 0
    n = _upsert_document(db, slug, title, source_type, text)
    db.commit()
    v = embed_pending_chunks(db)
    logger.info("ocr_ingest: %s -> %d chunks (%d vectors)", slug, n, v)
    return n


def make_sample_spec_pdf(path: str | Path = _SAMPLE) -> Path:
    """Render a sample product spec-sheet PDF (reportlab) for the PDF-ingest demo."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("BuildRight ProDrive 20V MAX Cordless Drill/Driver — Spec Sheet", styles["Title"]),
        Spacer(1, 12),
        Paragraph("Overview", styles["Heading2"]),
        Paragraph(
            "A brushless 20V MAX drill/driver with a 2-speed gearbox, keyless 1/2\" chuck, "
            "and LED work light. Ships with a 2.0Ah battery and charger.", styles["BodyText"]),
        Spacer(1, 8),
        Paragraph("Specifications", styles["Heading2"]),
        Table(
            [["Spec", "Value"],
             ["Voltage", "20V MAX"],
             ["Chuck", '1/2 in keyless'],
             ["Max torque", "65 Nm"],
             ["No-load speed", "0-450 / 0-1700 rpm"],
             ["Battery", "2.0Ah Li-ion"],
             ["Weight", "1.4 kg"]],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ])),
        Spacer(1, 8),
        Paragraph("Safety", styles["Heading2"]),
        Paragraph(
            "Wear eye protection. Remove the battery before changing bits. Do not expose to rain.",
            styles["BodyText"]),
    ]
    SimpleDocTemplate(str(path), pagesize=letter).build(story)
    return path


def main() -> None:
    from app.core.db import SessionLocal
    logging.basicConfig(level=logging.INFO)
    pdf = make_sample_spec_pdf()
    db = SessionLocal()
    try:
        n = ingest_pdf(db, pdf, "manual-prodrive-20v-drill", "ProDrive 20V Drill — Spec Sheet")
    finally:
        db.close()
    print(f"Built {pdf} and ingested {n} chunks.")


if __name__ == "__main__":
    main()
