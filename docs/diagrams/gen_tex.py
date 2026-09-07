"""Generate per-slide standalone TikZ .tex files for the About architecture slideshow.

Source: the design panel's slide specs (scratchpad/plan.json). We normalize the panel's
navy/burnt-orange palette to the app's Industrial Slate + Safety Amber tokens so the
diagrams match the UI. Output: docs/diagrams/slide-NN-<slug>.tex (committed; compiled to
SVG by build.sh -> frontend/public/diagrams/).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = Path(
    r"C:\Users\rashi\AppData\Local\Temp\claude\C--Users-rashi-OneDrive-Desktop-Cut-Dry"
    r"\baac6442-5434-4577-ac87-4579b73171f0\scratchpad\plan.json"
)

# Industrial Slate + Safety Amber remap of the panel's diagram palette.
COLOR_MAP = {
    "navy": "161E29",        # brand-900  (dark fills + heading text)
    "slate": "2E3D50",       # brand-700  (box borders + secondary text)
    "slatefill": "E9EDF2",   # brand-100  (light box fills)
    "accent": "B45309",      # accent-700 (AA-safe amber for borders/arrows on white)
    "accentfill": "FEF3C7",  # accent-light (amber wash)
    "edge": "51647D",        # brand-500  (neutral arrows)
}

SLUGS = {
    1: "overview", 2: "architecture", 3: "hybrid-rag", 4: "agent-loop",
    6: "multimodal", 7: "commerce", 8: "observability",
    9: "deployment",
}


def normalize(tikz: str) -> str:
    for name, new_hex in COLOR_MAP.items():
        tikz = re.sub(
            r"(\\definecolor\{" + name + r"\}\{HTML\}\{)[0-9A-Fa-f]{6}(\})",
            r"\g<1>" + new_hex + r"\g<2>",
            tikz,
        )
    return tikz


def main() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    slides = (plan.get("aboutSlides") or {}).get("slides", [])
    written = []
    for s in slides:
        n = int(s["n"])
        slug = SLUGS.get(n, f"slide{n}")
        tex = normalize(s["tikz"]).strip() + "\n"
        out = HERE / f"slide-{n:02d}-{slug}.tex"
        out.write_text(tex, encoding="utf-8")
        written.append(out.name)
    # Also emit a meta.json (title/subtitle/body/alt) for the React slides data.
    meta = [
        {"n": int(s["n"]), "slug": SLUGS.get(int(s["n"])), "title": s["title"],
         "subtitle": s.get("subtitle", ""), "body": s.get("body", ""), "alt": s.get("alt", "")}
        for s in slides
    ]
    (HERE / "slides_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"wrote {len(written)} tex files:", ", ".join(written))


if __name__ == "__main__":
    main()
