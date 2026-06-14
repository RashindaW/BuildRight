"""Vision helpers — image validation + reply parsing (keyless, no API)."""

from __future__ import annotations

import pytest

from app.ai import vision


def test_validate_image_accepts_jpeg():
    assert vision.validate_image(b"x" * 10, "image/jpeg") == "image/jpeg"


def test_validate_image_normalizes_charset_suffix():
    assert vision.validate_image(b"x", "image/png; charset=binary") == "image/png"


def test_validate_image_rejects_bad_type():
    with pytest.raises(vision.VisionError):
        vision.validate_image(b"x", "application/pdf")


def test_validate_image_rejects_empty():
    with pytest.raises(vision.VisionError):
        vision.validate_image(b"", "image/jpeg")


def test_validate_image_rejects_oversize():
    with pytest.raises(vision.VisionError):
        vision.validate_image(b"x" * (vision.MAX_IMAGE_BYTES + 1), "image/jpeg")


def test_clean_query_strips_punctuation():
    assert vision.clean_query("Cordless Drill/Driver!!") == "Cordless Drill Driver"


def test_parse_stock_json_well_formed():
    text = 'Here you go: [{"item": "BR-PWR-1", "qty": 12}, {"item": "Paint", "qty": 3}]'
    rows = vision.parse_stock_json(text)
    assert rows == [{"item": "BR-PWR-1", "qty": 12}, {"item": "Paint", "qty": 3}]


def test_parse_stock_json_skips_bad_rows():
    text = '[{"item": "ok", "qty": 5}, {"item": "", "qty": 2}, {"item": "x", "qty": "many"}, 42]'
    assert vision.parse_stock_json(text) == [{"item": "ok", "qty": 5}]


def test_parse_stock_json_no_array():
    assert vision.parse_stock_json("nothing readable") == []
