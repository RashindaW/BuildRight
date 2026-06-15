"""Category placeholder SVG renderer + endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.seed.placeholder_svg import CATEGORY_STYLE, _wrap, render_placeholder, style_for


def test_every_category_renders_valid_svg():
    for slug in list(CATEGORY_STYLE) + ["mystery-category"]:
        svg = render_placeholder(slug, "Sample Long Product Name Here")
        assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
        assert "{c}" not in svg  # every icon placeholder was filled


def test_label_is_escaped_and_present():
    svg = render_placeholder("paint", 'Roller & "Pro" Kit')
    assert "&amp;" in svg and "&quot;" in svg
    assert "<script" not in svg


def test_unknown_category_uses_default_style():
    color, _icon, label = style_for("not-a-real-cat")
    assert color.startswith("#") and label == "BuildRight"


def test_wrap_limits_lines_and_truncates():
    lines = _wrap("one two three four five six seven eight nine ten")
    assert len(lines) <= 2
    assert lines[-1].endswith("…")


def test_placeholder_endpoint_serves_cached_svg():
    c = TestClient(app)
    r = c.get("/api/v1/media/placeholder.svg", params={"cat": "power-tools", "label": "Cordless Drill"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/svg+xml")
    assert "max-age=31536000" in r.headers.get("cache-control", "")
    assert "POWER TOOLS" in r.text and "<svg" in r.text
