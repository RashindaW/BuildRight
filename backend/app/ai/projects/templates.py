"""Deterministic project templates.

Each template turns a room's measurements into a bill of materials — a list of
"roles" (interior paint, primer, tile, …) with a computed quantity. The math is
pure and unit-tested; the tool layer (ai/tools.py) then resolves each role to a
real catalog SKU and grounds its price.

All quantities round UP (you can't buy 0.6 of a gallon) and carry a small waste
factor where industry practice expects one. Assumptions are returned alongside
the list so the assistant can show its work to the shopper.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable


class ProjectPlanError(ValueError):
    """Raised when inputs are missing or out of a sane range."""


@dataclass(frozen=True)
class Material:
    role: str
    label: str
    query: str                       # catalog search to resolve a real SKU
    unit: str
    qty_fn: Callable[[dict], int]
    category: str | None = None
    optional: bool = False


@dataclass(frozen=True)
class ProjectTemplate:
    key: str
    label: str
    # required numeric inputs (feet); height_ft is optional with a default
    needs: tuple[str, ...]
    materials: tuple[Material, ...]
    assumptions: tuple[str, ...] = ()
    default_height_ft: float = 8.0
    default_coats: int = 2


def _ceil(x: float) -> int:
    return max(1, math.ceil(round(x, 6)))


# ---- Geometry --------------------------------------------------------------

def _geometry(length: float, width: float, height: float) -> dict:
    perimeter = 2 * (length + width)
    floor_area = length * width
    gross_wall = perimeter * height
    # Subtract ~10% for a door + windows (typical room).
    paintable_wall = gross_wall * 0.90
    return {
        "length_ft": length,
        "width_ft": width,
        "height_ft": height,
        "perimeter_ft": round(perimeter, 2),
        "floor_area_sqft": round(floor_area, 2),
        "wall_area_sqft": round(gross_wall, 2),
        "paintable_wall_sqft": round(paintable_wall, 2),
    }


# ---- Templates -------------------------------------------------------------

PAINT_COVERAGE = 350.0   # sqft per gallon per coat
PRIMER_COVERAGE = 400.0  # sqft per gallon (one coat)
TILE_BOX_SQFT = 15.0     # assumed coverage per box of ceramic tile
THINSET_SQFT = 80.0      # sqft per bag of tile adhesive
GROUT_SQFT = 150.0       # sqft per bag of grout
PLANK_BOX_SQFT = 20.0    # sqft per box of laminate / vinyl plank
UNDERLAYMENT_ROLL_SQFT = 100.0
DRYWALL_SHEET_SQFT = 32.0  # a 4x8 sheet
TRIM_PIECE_FT = 8.0


_TEMPLATES: dict[str, ProjectTemplate] = {}


def _register(t: ProjectTemplate) -> ProjectTemplate:
    _TEMPLATES[t.key] = t
    return t


_register(ProjectTemplate(
    key="paint_room",
    label="Paint a room",
    needs=("length_ft", "width_ft"),
    assumptions=(
        f"Paint covers ~{int(PAINT_COVERAGE)} sq ft per gallon per coat; default 2 coats.",
        "Walls computed from room perimeter × height, less ~10% for a door and windows.",
        "Primer is one coat; tape sized to the room perimeter.",
    ),
    materials=(
        Material("paint", "Interior paint", "interior paint latex", "gallon",
                 lambda g: _ceil(g["paintable_wall_sqft"] * g["coats"] / PAINT_COVERAGE),
                 category="paint"),
        Material("primer", "Primer", "primer undercoat stain block", "gallon",
                 lambda g: _ceil(g["paintable_wall_sqft"] / PRIMER_COVERAGE),
                 category="paint", optional=True),
        Material("roller", "Paint roller kit", "paint roller kit", "kit",
                 lambda g: 1, category="paint"),
        Material("brush", "Paint brush set", "paint brush set trim", "set",
                 lambda g: 1, category="paint"),
        Material("tape", "Painter's tape", "painters tape masking", "roll",
                 lambda g: _ceil(g["perimeter_ft"] / 60.0), category="paint"),
        Material("dropcloth", "Drop cloth", "drop cloth canvas", "each",
                 lambda g: _ceil(g["floor_area_sqft"] / 120.0), category="paint"),
    ),
))

_register(ProjectTemplate(
    key="tile_floor",
    label="Tile a floor",
    needs=("length_ft", "width_ft"),
    assumptions=(
        f"Tile ordered with a 10% waste/cuts factor (~{int(TILE_BOX_SQFT)} sq ft per box).",
        f"Adhesive ~{int(THINSET_SQFT)} sq ft per bag; grout ~{int(GROUT_SQFT)} sq ft per bag.",
        "Floor trim sized to the room perimeter.",
    ),
    materials=(
        Material("tile", "Ceramic tile", "ceramic floor tile", "box",
                 lambda g: _ceil(g["floor_area_sqft"] * 1.10 / TILE_BOX_SQFT),
                 category="flooring"),
        Material("adhesive", "Tile adhesive", "tile adhesive thinset mortar", "bag",
                 lambda g: _ceil(g["floor_area_sqft"] / THINSET_SQFT),
                 category="flooring"),
        Material("grout", "Grout", "tile grout", "bag",
                 lambda g: _ceil(g["floor_area_sqft"] / GROUT_SQFT),
                 category="flooring"),
        Material("trim", "Floor trim", "floor trim baseboard quarter round", "piece",
                 lambda g: _ceil(g["perimeter_ft"] / TRIM_PIECE_FT),
                 category="flooring", optional=True),
    ),
))

_register(ProjectTemplate(
    key="laminate_floor",
    label="Install laminate / vinyl flooring",
    needs=("length_ft", "width_ft"),
    assumptions=(
        f"Planks ordered with an 8% waste factor (~{int(PLANK_BOX_SQFT)} sq ft per box).",
        f"Underlayment ~{int(UNDERLAYMENT_ROLL_SQFT)} sq ft per roll.",
        "Quarter-round trim sized to the room perimeter.",
    ),
    materials=(
        Material("plank", "Laminate flooring", "laminate flooring planks", "box",
                 lambda g: _ceil(g["floor_area_sqft"] * 1.08 / PLANK_BOX_SQFT),
                 category="flooring"),
        Material("underlayment", "Underlayment", "underlayment foam subfloor", "roll",
                 lambda g: _ceil(g["floor_area_sqft"] / UNDERLAYMENT_ROLL_SQFT),
                 category="flooring"),
        Material("trim", "Floor trim", "floor trim quarter round baseboard", "piece",
                 lambda g: _ceil(g["perimeter_ft"] / TRIM_PIECE_FT),
                 category="flooring", optional=True),
    ),
))

_register(ProjectTemplate(
    key="drywall_room",
    label="Drywall a room",
    needs=("length_ft", "width_ft"),
    assumptions=(
        f"Drywall ordered with a 10% waste factor (4×8 sheet = {int(DRYWALL_SHEET_SQFT)} sq ft).",
        "Walls computed from room perimeter × height, less ~10% for openings.",
    ),
    materials=(
        Material("drywall", "Drywall sheet", "drywall sheet wallboard", "sheet",
                 lambda g: _ceil(g["paintable_wall_sqft"] * 1.10 / DRYWALL_SHEET_SQFT),
                 category="building-materials"),
        Material("screws", "Drywall screws", "drywall screws", "pack",
                 lambda g: _ceil(g["paintable_wall_sqft"] / 200.0),
                 category="fasteners"),
        Material("tape", "Drywall / construction adhesive", "construction adhesive", "tube",
                 lambda g: _ceil(g["paintable_wall_sqft"] / 250.0),
                 category="building-materials", optional=True),
    ),
))


PROJECT_TYPES = tuple(_TEMPLATES.keys())


# ---- Public API ------------------------------------------------------------

def _coerce_float(value, name: str) -> float:
    try:
        f = float(value)
    except (TypeError, ValueError):
        raise ProjectPlanError(f"'{name}' must be a number (feet).")
    if not (0 < f <= 200):
        raise ProjectPlanError(f"'{name}' must be between 0 and 200 feet.")
    return f


def plan_materials(project_type: str, params: dict) -> dict:
    """Compute a bill of materials for a project.

    params accepts: length_ft, width_ft, height_ft (optional), coats (optional).
    Returns a dict with the geometry, assumptions, and a list of
    {role, label, query, category, unit, quantity} materials. Pure / no I/O.
    """
    template = _TEMPLATES.get(project_type)
    if template is None:
        raise ProjectPlanError(
            f"Unknown project type '{project_type}'. "
            f"Supported: {', '.join(PROJECT_TYPES)}."
        )

    params = params or {}
    length = _coerce_float(params.get("length_ft"), "length_ft")
    width = _coerce_float(params.get("width_ft"), "width_ft")
    height = params.get("height_ft")
    height = _coerce_float(height, "height_ft") if height is not None else template.default_height_ft

    coats = params.get("coats")
    try:
        coats = int(coats) if coats is not None else template.default_coats
    except (TypeError, ValueError):
        coats = template.default_coats
    coats = max(1, min(coats, 4))

    geom = _geometry(length, width, height)
    geom["coats"] = coats

    include_optional = bool(params.get("include_optional", True))
    materials = []
    for m in template.materials:
        if m.optional and not include_optional:
            continue
        qty = m.qty_fn(geom)
        materials.append({
            "role": m.role,
            "label": m.label,
            "query": m.query,
            "category": m.category,
            "unit": m.unit,
            "quantity": qty,
            "optional": m.optional,
        })

    return {
        "project_type": template.key,
        "label": template.label,
        "dimensions": {
            "length_ft": length, "width_ft": width,
            "height_ft": height, "coats": coats,
        },
        "derived": {
            "perimeter_ft": geom["perimeter_ft"],
            "floor_area_sqft": geom["floor_area_sqft"],
            "wall_area_sqft": geom["wall_area_sqft"],
            "paintable_wall_sqft": geom["paintable_wall_sqft"],
        },
        "assumptions": list(template.assumptions),
        "materials": materials,
    }
