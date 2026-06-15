"""Richer, heterogeneous per-CATEGORY guides for the vector knowledge base.

Unlike the short per-type buying guides, these are longer, multi-section documents
with **comparison tables**, how-to-choose prose, installation/usage, troubleshooting,
safety, and care — closer to a real retailer's content library. Generated from the
catalog so they stay in sync, ingested through the same KB pipeline (chunked + embedded).
Pure + free (no LLM, no network).
"""

from __future__ import annotations

import re

from app.seed.catalog_generator import AXES, CATEGORIES

_AXIS_SHORT = {
    "VOLT": "12V–60V", "GRADE": "Standard/Pro", "SIZE_IN": '1/4"–1"', "PACK": "10–250 pack",
    "LEN_FT": "25–150 ft", "CAP": "5–40 L", "GRIT": "60–220 grit", "COLOUR": "multiple finishes",
    "AMP": "3–12 A", "SIZE_S": "Compact–XL", "WATT": "40–150 W",
}

_FLAG_SAFE = {
    "contains-battery": "Store and charge batteries per the manual; don't leave on charge unattended.",
    "sharp-blade": "Keep guards on; wear eye protection and cut-resistant gloves.",
    "power-tool": "Read the manual; wear eye and ear protection; unplug before changing accessories.",
    "flammable": "Store away from heat/ignition; use in a ventilated area.",
    "heavy-item": "Use proper lifting technique or a cart; may ship by freight.",
    "requires-assembly": "Follow the assembly sequence; keep all hardware until finished.",
}


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:90]


def _category_markdown(cat: dict) -> str:
    label = cat["label"]
    types = cat["types"]
    lines = [
        f"# {label} — Category Guide",
        "",
        "## Overview",
        f"BuildRight AI's {label.lower()} range covers "
        f"{', '.join(t['name'] for t in types[:8])}"
        f"{' and more' if len(types) > 8 else ''}. This guide helps you choose, install, "
        "and maintain them.",
        "",
        "## Choosing the right product",
        "| Product | Good for | Options |",
        "|---|---|---|",
    ]
    for t in types:
        good_for = (t["kw"][0] if t.get("kw") else t["name"]).replace('"', "")
        lines.append(f"| {t['name']} | {good_for} | {_AXIS_SHORT.get(t['axis'], 'see specs')} |")

    lines += [
        "",
        "## How to choose",
        "- Match the product to your most common task, then size up one tier if you'll use it often.",
        "- Cordless trades runtime for portability; corded gives unlimited runtime. Check battery platform compatibility before buying.",
        "- Buy consumables (blades, bits, abrasives, fasteners) in the pack size that matches your project volume.",
        "",
        "## Installation & use",
        "- Read the included manual first; keep packaging until the item is confirmed working.",
        "- Test fit / dry-run before committing (cuts, fasteners, paint colour).",
        "",
        "## Troubleshooting",
        "- Underperforming cordless tool → charge or swap the battery; check for a worn accessory.",
        "- Poor finish/cut → step through the correct grit/blade; let the tool do the work, don't force it.",
        "- Leaks/loose fittings → re-seat with the correct sealant/tape and torque.",
    ]

    flags = sorted({f for t in types for f in t.get("flags", []) if f in _FLAG_SAFE})
    if flags:
        lines += ["", "## Safety"] + [f"- {_FLAG_SAFE[f]}" for f in flags]

    lines += [
        "",
        "## Care & maintenance",
        "- Wipe down after use; store dry. Charge batteries to ~50% for long storage.",
        "- Register for warranty where applicable and keep your receipt for returns/price-match.",
        "",
    ]
    return "\n".join(lines)


def generate_category_guides() -> list[dict]:
    """Return [{slug, title, text}] — one rich guide per category (~19)."""
    out: list[dict] = []
    for cat in CATEGORIES:
        out.append({
            "slug": f"catguide-{_slugify(cat['label'])}",
            "title": f"{cat['label']} Category Guide",
            "text": _category_markdown(cat),
        })
    return out
