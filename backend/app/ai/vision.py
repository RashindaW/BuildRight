"""Claude vision helpers — image → product search phrase, and handwritten
count-sheet OCR.

Live calls need a real ANTHROPIC_API_KEY (vision runs on Haiku/Sonnet). Image
validation and reply parsing are pure and defensive, so a malformed model reply
or an oversized upload never raises into the request handler.
"""

from __future__ import annotations

import base64
import json
import logging
import re

import anthropic

from app.core.config import settings

logger = logging.getLogger("app.ai.vision")

ALLOWED_MEDIA = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB


class VisionError(Exception):
    """Raised for an invalid/oversized image (mapped to HTTP 422 by the router)."""


def validate_image(data: bytes, media_type: str | None) -> str:
    """Validate bytes + media type; returns the normalized media type."""
    mt = (media_type or "").split(";")[0].strip().lower()
    if mt not in ALLOWED_MEDIA:
        raise VisionError("Unsupported image type. Use JPEG, PNG, WEBP, or GIF.")
    if not data:
        raise VisionError("The image is empty.")
    if len(data) > MAX_IMAGE_BYTES:
        raise VisionError("Image too large (max 5 MB).")
    return mt


def _image_block(data: bytes, media_type: str) -> dict:
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": base64.standard_b64encode(data).decode("ascii"),
        },
    }


def _client() -> anthropic.Anthropic:
    # Reuse the assistant's lazily-built sync client.
    from app.ai.service import _get_sync_client
    return _get_sync_client()


def _text_of(resp) -> str:
    return "".join(b.text for b in resp.content if b.type == "text").strip()


# ---- Find-this-item -------------------------------------------------------

_FIND_SYSTEM = (
    "You identify hardware-store products from a photo. Reply with ONLY a short "
    "2-6 word product search query (e.g. 'cordless drill', 'paint roller kit'). "
    "No punctuation, no full sentences."
)


def clean_query(text: str) -> str:
    text = re.sub(r"[^\w\s-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()[:80]


def describe_image_for_search(data: bytes, media_type: str | None, *, model: str | None = None) -> str:
    """Return a short catalog search phrase for the pictured product, or '' on failure."""
    mt = validate_image(data, media_type)
    try:
        resp = _client().messages.create(
            model=model or settings.llm_model_heavy,
            max_tokens=30,
            temperature=0.0,
            system=_FIND_SYSTEM,
            messages=[{"role": "user", "content": [
                _image_block(data, mt),
                {"type": "text", "text": "What product is this? Give a short catalog search query."},
            ]}],
        )
    except (anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.APIError) as e:
        logger.warning('"vision_describe_failed: %s"', type(e).__name__)
        return ""
    return clean_query(_text_of(resp))


# ---- Handwritten count-sheet OCR ------------------------------------------

_STOCK_SYSTEM = (
    "You read an inventory count sheet (often handwritten) from an image. Extract "
    "each line as an object {\"item\": <product name or SKU exactly as written>, "
    "\"qty\": <integer count>}. Reply with ONLY a JSON array of those objects. "
    "If nothing is readable, reply with []."
)


def parse_stock_json(text: str) -> list[dict]:
    """Defensively parse the model's reply into [{item, qty}] rows."""
    match = re.search(r"\[.*\]", text, re.S)
    if not match:
        return []
    try:
        rows = json.loads(match.group(0))
    except (ValueError, json.JSONDecodeError):
        return []
    out: list[dict] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        item = str(row.get("item", "")).strip()[:120]
        try:
            qty = int(row.get("qty"))
        except (TypeError, ValueError):
            continue
        if item and qty >= 0:
            out.append({"item": item, "qty": qty})
    return out


def extract_stock_counts(data: bytes, media_type: str | None, *, model: str | None = None) -> list[dict]:
    """OCR a count sheet → [{item, qty}]. Returns [] on failure."""
    mt = validate_image(data, media_type)
    try:
        resp = _client().messages.create(
            model=model or settings.llm_model_heavy,
            max_tokens=1500,
            temperature=0.0,
            system=_STOCK_SYSTEM,
            messages=[{"role": "user", "content": [
                _image_block(data, mt),
                {"type": "text", "text": "Extract the item/quantity rows as a JSON array."},
            ]}],
        )
    except (anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.APIError) as e:
        logger.warning('"vision_ocr_failed: %s"', type(e).__name__)
        return []
    return parse_stock_json(_text_of(resp))


# ---- Manual / document OCR → knowledge base -------------------------------

_OCR_DOC_SYSTEM = (
    "You transcribe a product manual or spec sheet from an image into clean Markdown. "
    "Preserve headings (##), bullet lists, and any spec TABLE as a Markdown table. "
    "Transcribe only what is visible; do not invent content. Reply with ONLY the Markdown."
)


def ocr_image_to_text(data: bytes, media_type: str | None, *, model: str | None = None) -> str:
    """OCR a scanned manual/spec page into Markdown (for KB ingestion). '' on failure.

    This turns a photographed manual into a vector-searchable document — the OCR
    counterpart to the digital PDF arm. Needs a live ANTHROPIC_API_KEY.
    """
    mt = validate_image(data, media_type)
    try:
        resp = _client().messages.create(
            model=model or settings.llm_model_heavy,
            max_tokens=2000,
            temperature=0.0,
            system=_OCR_DOC_SYSTEM,
            messages=[{"role": "user", "content": [
                _image_block(data, mt),
                {"type": "text", "text": "Transcribe this page to Markdown."},
            ]}],
        )
    except (anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.APIError) as e:
        logger.warning('"vision_doc_ocr_failed: %s"', type(e).__name__)
        return ""
    return _text_of(resp)
