"""Deterministic per-TYPE buying-guide documents for the vector knowledge base.

For each product TYPE in the catalog generator (~195), emit a short markdown
"buying guide" so the assistant can answer "how do I choose / what's the
difference between X and Y" with grounded, cited content via the existing KB
pipeline. Pure + free (no LLM, no network); concise to keep chunk count low.
"""

from __future__ import annotations

import re

from app.seed.catalog_generator import AXES, CATEGORIES

# How each variant axis trades off — explained once, reused across types.
_AXIS_NOTE = {
    "VOLT": "Higher voltage means more power and runtime but more weight: 12V for light/overhead work, 18–20V MAX for everyday jobs, 40–60V for heavy or outdoor use.",
    "GRADE": "Standard suits occasional DIY; Pro / Heavy-Duty are built for daily or jobsite use; Compact trades capacity for tight spaces.",
    "SIZE_IN": "Match the size to your fasteners or stock — too small bottoms out, too large won't seat.",
    "PACK": "Bigger packs cost less per unit — buy the pack that matches your project volume.",
    "LEN_FT": "Pick a length with a little slack; longer gives more reach but more to store.",
    "CAP": "Larger capacity means fewer refills/recharges for bigger jobs.",
    "GRIT": "Lower grit removes material fast; higher grit leaves a finer finish — step up through grits.",
    "COLOUR": "Choose a finish to match your existing fixtures and hardware.",
    "AMP": "Higher amperage delivers more sustained power for tougher, longer cuts.",
    "SIZE_S": "Compact for tight spaces and portability; larger for capacity and coverage.",
    "WATT": "Higher wattage means more output — brighter light or more heat.",
}

# Safety/handling notes keyed on the type's flags.
_FLAG_NOTE = {
    "contains-battery": "Uses/ships with a battery — check platform compatibility before buying.",
    "sharp-blade": "Has a sharp blade or edge — wear eye protection and cut-resistant gloves.",
    "power-tool": "Power tool — read the manual and wear eye and ear protection.",
    "flammable": "Flammable — store away from heat and ignition sources; ensure ventilation.",
    "heavy-item": "Heavy item — may ship by freight; plan for lifting help.",
    "requires-assembly": "Some assembly is required.",
}

_TAG_NOTE = {
    "cordless": "cordless for portability",
    "corded": "corded for unlimited runtime",
    "professional": "pro-grade for heavy or daily use",
    "outdoor": "rated for outdoor use",
    "battery-powered": "battery powered",
}


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:90]


def _guide_markdown(type_name: str, cat_label: str, spec: str, kw: list[str],
                    axis: str, tags: list[str], flags: list[str]) -> str:
    axis_vals = ", ".join(label for label, _ in AXES.get(axis, []) if label) or "a few options"
    lines = [
        f"# {type_name} — Buying Guide",
        "",
        f"Category: {cat_label}. {spec}",
        "",
        "## How to choose",
        f"- Available as: {axis_vals}. {_AXIS_NOTE.get(axis, 'Pick the option that matches your job.')}",
    ]
    tag_notes = [_TAG_NOTE[t] for t in tags if t in _TAG_NOTE]
    if tag_notes:
        lines.append(f"- This product line is {', '.join(tag_notes)}.")
    lines.append(f"- Common search terms: {', '.join(kw)}.")

    flag_notes = [_FLAG_NOTE[f] for f in flags if f in _FLAG_NOTE]
    if flag_notes:
        lines += ["", "## Safety & handling"] + [f"- {n}" for n in flag_notes]

    lines += [
        "",
        "## Tip",
        f"- Use the search to compare {type_name.lower()} options by price and stock, "
        "or ask the assistant to recommend one for your project.",
        "",
    ]
    return "\n".join(lines)


def generate_guides() -> list[dict]:
    """Return [{slug, title, text}] — one buying guide per product TYPE."""
    guides: list[dict] = []
    seen: set[str] = set()
    for cat in CATEGORIES:
        for ptype in cat["types"]:
            name = ptype["name"]
            slug = f"guide-{_slugify(name)}"
            if slug in seen:
                continue
            seen.add(slug)
            guides.append({
                "slug": slug,
                "title": f"{name} Buying Guide",
                "text": _guide_markdown(
                    name, cat["label"], ptype["spec"], ptype["kw"],
                    ptype["axis"], ptype["tags"], ptype["flags"],
                ),
            })
    return guides
