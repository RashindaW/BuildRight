"""Per-type buying-guide generation (keyless, pure)."""

from __future__ import annotations

from app.seed.product_guides import generate_guides


def test_generates_one_guide_per_type():
    guides = generate_guides()
    assert 150 <= len(guides) <= 250
    slugs = [g["slug"] for g in guides]
    assert len(slugs) == len(set(slugs))  # unique
    assert all(g["slug"].startswith("guide-") for g in guides)


def test_guide_has_title_and_markdown():
    g = next(x for x in generate_guides() if "drill" in x["slug"])
    assert g["title"].endswith("Buying Guide")
    assert g["text"].startswith("# ")
    assert "## How to choose" in g["text"]
