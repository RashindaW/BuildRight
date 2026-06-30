"""Deterministic, category-aware product placeholders rendered as SVG.

A hardware catalog of 10k SKUs has no real photos — and a random scenic stock
photo on a drill looks broken. Instead we render a clean, branded placeholder per
product: the category's colour + a simple line icon + the product label. It's an
SVG built on the fly (served by /media/placeholder.svg), so there are ZERO image
files to ship, it scales to any catalog size, and it always renders offline.

Pure + dependency-free: `render_placeholder(category, label)` returns SVG markup.
"""

from __future__ import annotations

import hashlib
import html

# Each category: a distinct accent colour + a simple 24x24 line/solid icon.
# Icons use the category colour via `{c}`; drawn inside a 0..24 viewBox.
_BOLT = '<path d="M13 2 5 14h6l-1 8 9-12h-6z" fill="{c}"/>'
_HAMMER = ('<rect x="5" y="4" width="11" height="4" rx="1" fill="{c}"/>'
           '<rect x="9.5" y="8" width="2.6" height="12" rx="1.1" fill="{c}"/>')
_SCREW = ('<polygon points="9,3 15,3 17,7 15,11 9,11 7,7" fill="{c}"/>'
          '<path d="M10 11v9M14 11v9" stroke="{c}" stroke-width="1.6"/>'
          '<path d="M10 13.5h4M10 16h4M10 18.5h4" stroke="{c}" stroke-width="1.4"/>')
_KEY = ('<circle cx="8" cy="8" r="4" fill="none" stroke="{c}" stroke-width="2.2"/>'
        '<path d="M11 11l8 8M16 16l2-2M18.5 18.5l1.8-1.8" stroke="{c}" stroke-width="2.2"/>')
_CAR = ('<path d="M4 13l2-5h9l3 5" fill="none" stroke="{c}" stroke-width="1.8"/>'
        '<rect x="3" y="13" width="18" height="4.5" rx="1.2" fill="{c}"/>'
        '<circle cx="7.5" cy="18.5" r="2" fill="#fff" stroke="{c}" stroke-width="1.6"/>'
        '<circle cx="16.5" cy="18.5" r="2" fill="#fff" stroke="{c}" stroke-width="1.6"/>')
_POT = ('<rect x="5" y="9" width="14" height="9" rx="1.6" fill="{c}"/>'
        '<path d="M3 11h2M19 11h2M7 9h10M12 5.5v3.5" stroke="{c}" stroke-width="1.8"/>')
_TREE = ('<polygon points="12,3 7,11 17,11" fill="{c}"/>'
         '<polygon points="12,8 6,17 18,17" fill="{c}"/>'
         '<rect x="11" y="17" width="2" height="3.5" fill="{c}"/>')
_LEAF = ('<path d="M12 21c0-7 3-11 9-12-1 7-4 11-9 12z" fill="{c}"/>'
         '<path d="M12 21v-7" stroke="{c}" stroke-width="1.6"/>')
_SPRAY = ('<rect x="8" y="9" width="7" height="11" rx="1.6" fill="{c}"/>'
          '<rect x="9" y="5.5" width="3" height="3.5" fill="{c}"/>'
          '<path d="M9 6.5H5l-2 2" fill="none" stroke="{c}" stroke-width="1.6"/>'
          '<circle cx="3" cy="4.5" r=".7" fill="{c}"/><circle cx="5" cy="3.5" r=".7" fill="{c}"/>')
_ROLLER = ('<rect x="5" y="5" width="12" height="5" rx="1.6" fill="{c}"/>'
           '<path d="M11 10v3H7v2" fill="none" stroke="{c}" stroke-width="1.8"/>'
           '<rect x="5.5" y="15" width="3" height="5.5" rx="1.2" fill="{c}"/>')
_PLUG = ('<path d="M9 2v5M15 2v5" stroke="{c}" stroke-width="1.8"/>'
         '<path d="M7 7h10v3a5 5 0 0 1-10 0z" fill="{c}"/>'
         '<path d="M12 15v6" stroke="{c}" stroke-width="1.8"/>')
_DROP = '<path d="M12 3c4 5 6.5 8.5 6.5 11.5a6.5 6.5 0 0 1-13 0C5.5 11.5 8 8 12 3z" fill="{c}"/>'
_BULB = ('<circle cx="12" cy="10" r="5.5" fill="{c}"/>'
         '<path d="M9 17h6M10 20h4" stroke="{c}" stroke-width="1.8"/>')
_BRICKS = ('<rect x="3" y="6" width="8" height="4" rx=".6" fill="{c}"/>'
           '<rect x="13" y="6" width="8" height="4" rx=".6" fill="{c}"/>'
           '<rect x="8" y="11" width="8" height="4" rx=".6" fill="{c}"/>'
           '<rect x="3" y="16" width="8" height="4" rx=".6" fill="{c}"/>'
           '<rect x="13" y="16" width="8" height="4" rx=".6" fill="{c}"/>')
_BOX = ('<path d="M3 7l9-4 9 4-9 4z" fill="{c}"/>'
        '<path d="M3 7v8l9 4 9-4V7M12 11v8" fill="none" stroke="{c}" stroke-width="1.8"/>')
_HARDHAT = ('<path d="M4 16a8 8 0 0 1 16 0z" fill="{c}"/>'
            '<rect x="2" y="16" width="20" height="2.6" rx="1.2" fill="{c}"/>'
            '<path d="M12 8.5v3.5M9 9.5v2.5M15 9.5v2.5" stroke="#fff" stroke-width="1.4"/>')
_SNOW = ('<path d="M12 2v20M3.3 7l17.4 10M20.7 7L3.3 17" stroke="{c}" stroke-width="1.8"/>'
         '<path d="M12 5l-2-2M12 5l2-2M12 19l-2 2M12 19l2 2" stroke="{c}" stroke-width="1.6"/>')
_PLANKS = ('<rect x="3" y="5" width="18" height="3.6" rx=".5" fill="{c}"/>'
           '<rect x="3" y="10.2" width="18" height="3.6" rx=".5" fill="{c}"/>'
           '<rect x="3" y="15.4" width="18" height="3.6" rx=".5" fill="{c}"/>')
_SUN = ('<circle cx="12" cy="12" r="4.5" fill="{c}"/>'
        '<path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2" '
        'stroke="{c}" stroke-width="1.8"/>')
_TENT = ('<path d="M12 5 3 19h18z" fill="{c}"/>'
         '<path d="M12 11l-3.2 8M12 11l3.2 8" stroke="#fff" stroke-width="1.5"/>')

# slug -> (accent colour, icon markup, display label)
CATEGORY_STYLE: dict[str, tuple[str, str, str]] = {
    "power-tools": ("#ea580c", _BOLT, "Power Tools"),
    "hand-tools": ("#0891b2", _HAMMER, "Hand Tools"),
    "fasteners": ("#475569", _SCREW, "Fasteners"),
    "hardware": ("#b45309", _KEY, "Hardware"),
    "automotive": ("#1e40af", _CAR, "Automotive"),
    "kitchen": ("#db2777", _POT, "Kitchen"),
    "outdoor": ("#15803d", _TREE, "Outdoor"),
    "lawn-garden": ("#16a34a", _LEAF, "Lawn & Garden"),
    "cleaning": ("#0ea5e9", _SPRAY, "Cleaning"),
    "paint": ("#7c3aed", _ROLLER, "Paint"),
    "electrical": ("#ca8a04", _PLUG, "Electrical"),
    "plumbing": ("#0284c7", _DROP, "Plumbing"),
    "lighting": ("#f59e0b", _BULB, "Lighting"),
    "building-materials": ("#78716c", _BRICKS, "Building Materials"),
    "storage": ("#4f46e5", _BOX, "Storage"),
    "safety": ("#dc2626", _HARDHAT, "Safety"),
    "heating-cooling": ("#0d9488", _SNOW, "Heating & Cooling"),
    "flooring": ("#92400e", _PLANKS, "Flooring"),
    "seasonal": ("#e11d48", _SUN, "Seasonal"),
    "sporting": ("#059669", _TENT, "Sporting"),
}
_DEFAULT_STYLE = ("#475569", _BOX, "BuildRight")


def _mix(hex_color: str, white_frac: float) -> str:
    """Blend a #rrggbb colour toward white by white_frac (0..1)."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    r = round(r + (255 - r) * white_frac)
    g = round(g + (255 - g) * white_frac)
    b = round(b + (255 - b) * white_frac)
    return f"#{r:02x}{g:02x}{b:02x}"


def _wrap(label: str, width: int = 16, max_lines: int = 2) -> list[str]:
    """Greedy word-wrap into at most max_lines, with an ellipsis if it overflows."""
    words = label.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        cand = f"{cur} {w}".strip()
        if len(cand) <= width or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = w
        if len(lines) == max_lines:
            break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if not lines:
        lines = [label[:width]]
    # If content remains beyond the last rendered line, mark truncation.
    rendered = " ".join(lines)
    if len(rendered) < len(label):
        last = lines[-1]
        lines[-1] = (last[: width - 1].rstrip() + "…") if len(last) >= width else last + "…"
    return lines


def style_for(category: str) -> tuple[str, str, str]:
    return CATEGORY_STYLE.get(category, _DEFAULT_STYLE)


def _variation(seed_text: str) -> float:
    """Deterministic 0.45..0.95 gradient-angle factor per product, so a grid of the same
    category isn't identical tiles (pure hash — stable across processes/runs)."""
    h = int(hashlib.sha256(seed_text.encode()).hexdigest()[:8], 16)
    return round(0.45 + (h % 50) / 100.0, 2)


def render_placeholder(category: str, label: str, *, width: int = 600, height: int = 400) -> str:
    """Return SVG markup for a product placeholder — an industrial dark-slate tile: a
    graphite ground with a category-tinted glow + engineering grid, a large light icon on
    a soft chip, the product label, and a BuildRight lockup with an UPPERCASE category tag.
    """
    color, icon, cat_label = style_for(category)
    safe_label = label or cat_label
    gy2 = _variation(safe_label)

    icon_color = _mix(color, 0.45)   # bright category tint that pops on the dark ground
    eyebrow_color = _mix(color, 0.40)
    icon_svg = icon.format(c=icon_color)

    cx, cy_icon = width / 2, height * 0.42
    chip = 80
    scale = (chip * 1.35) / 24.0
    tx = cx - 12 * scale
    ty = cy_icon - 12 * scale

    lines = _wrap(safe_label)
    label_y = height * 0.77
    label_spans = "".join(
        f'<tspan x="{cx}" dy="{0 if i == 0 else 30}">{html.escape(ln)}</tspan>'
        for i, ln in enumerate(lines)
    )
    esc = html.escape(safe_label)

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{esc}">'
        f'<defs>'
        f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="{gy2}">'
        f'<stop offset="0" stop-color="#1e293b"/><stop offset="1" stop-color="#0f172a"/>'
        f'</linearGradient>'
        f'<radialGradient id="glow" cx="0.5" cy="0.42" r="0.55">'
        f'<stop offset="0" stop-color="{color}" stop-opacity="0.34"/>'
        f'<stop offset="1" stop-color="{color}" stop-opacity="0"/>'
        f'</radialGradient>'
        f'<radialGradient id="vig" cx="0.5" cy="0.5" r="0.75">'
        f'<stop offset="0.6" stop-color="#000000" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="#000000" stop-opacity="0.28"/>'
        f'</radialGradient>'
        f'<pattern id="grid" width="26" height="26" patternUnits="userSpaceOnUse">'
        f'<path d="M26 0H0V26" fill="none" stroke="#ffffff" stroke-width="0.6"/>'
        f'</pattern>'
        f'</defs>'
        f'<rect width="{width}" height="{height}" fill="url(#bg)"/>'
        f'<rect width="{width}" height="{height}" fill="url(#grid)" opacity="0.06"/>'
        f'<rect width="{width}" height="{height}" fill="url(#glow)"/>'
        f'<rect x="{cx - chip:.0f}" y="{cy_icon - chip:.0f}" width="{2 * chip}" height="{2 * chip}" '
        f'rx="24" fill="#ffffff" fill-opacity="0.05" stroke="#ffffff" stroke-opacity="0.12"/>'
        f'<g transform="translate({tx:.1f},{ty:.1f}) scale({scale:.3f})" '
        f'fill="none" stroke-linecap="round" stroke-linejoin="round">{icon_svg}</g>'
        f'<text x="{cx}" y="{label_y}" text-anchor="middle" '
        f'font-family="Inter,system-ui,Segoe UI,Roboto,Helvetica,Arial,sans-serif" '
        f'font-size="30" font-weight="700" fill="#f1f5f9">{label_spans}</text>'
        f'<rect x="24" y="22" width="16" height="16" rx="4" fill="#f59e0b"/>'
        f'<text x="47" y="35" font-family="Inter,system-ui,Segoe UI,Roboto,sans-serif" '
        f'font-size="17" font-weight="800" fill="#e2e8f0">BuildRight</text>'
        f'<text x="{width - 24}" y="{height - 22}" text-anchor="end" '
        f'font-family="Inter,system-ui,Segoe UI,Roboto,sans-serif" font-size="15" '
        f'font-weight="700" letter-spacing="2" fill="{eyebrow_color}">'
        f'{html.escape(cat_label.upper())}</text>'
        f'<rect width="{width}" height="{height}" fill="url(#vig)"/>'
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" fill="none" '
        f'stroke="#ffffff" stroke-opacity="0.10"/>'
        f'</svg>'
    )
