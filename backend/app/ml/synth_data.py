"""Synthetic labeled data for the route classifier.

Generates (text, label) pairs where label ∈ {simple, complex}, grounded in the real
catalog vocabulary (product types/keywords from catalog_generator) so the model
learns domain-realistic phrasing. Deterministic (seeded) and dependency-free.

  simple  = single lookup / price / stock / policy / reorder / order-status
  complex = multi-step: project planning, materials math, comparing many options
"""

from __future__ import annotations

import random

from app.seed.catalog_generator import CATEGORIES

LABELS = ["simple", "complex"]
LABEL2ID = {l: i for i, l in enumerate(LABELS)}


def _vocab() -> tuple[list[str], list[str]]:
    """Product type names + keywords pulled from the real catalog."""
    types, keywords = [], []
    for cat in CATEGORIES:
        for t in cat["types"]:
            types.append(t["name"].split("/")[0].strip().lower())
            keywords.extend(t["kw"])
    return sorted(set(types)), sorted(set(keywords))


_SIMPLE_TEMPLATES = [
    "do you have {p}",
    "how much is the {p}",
    "what's the price of a {p}",
    "is the {p} in stock",
    "show me {p}s",
    "where are the {p}s",
    "i need a {p}",
    "do you sell {p}",
    "can i reorder my {p}",
    "reorder the {p}",
    "what's your return policy",
    "how long do i have to return something",
    "do you price match",
    "what's the warranty on the {p}",
    "where is my order",
    "what did i buy last time",
    "add the {p} to my cart",
    "is the {p} available",
]

_COMPLEX_TEMPLATES = [
    "i want to paint my {n} by {n} foot room, what do i need",
    "help me build a {n} foot fence",
    "i'm renovating my bathroom, what materials should i get",
    "plan a deck build for a {n} by {n} patio",
    "what's the difference between a {p} and a {p2}",
    "compare all your {p}s and tell me the best value",
    "i want to tile my kitchen floor, it's {n} by {n} feet",
    "which {p} should i get for a beginner vs a pro",
    "i'm repairing my room, walk me through what to buy",
    "estimate the materials and cost to redo my {n} by {n} basement",
    "how do i choose between a {p} and a {p2}",
    "i need everything to install laminate in a {n}x{n} room",
    "put together a shopping list to fix my leaking {p}",
    "what do i need to mount a {p} and seal around it",
]


def generate(n: int = 1600, seed: int = 7) -> list[dict]:
    rng = random.Random(seed)
    types, keywords = _vocab()
    terms = types + keywords
    rows: list[dict] = []
    per = n // 2
    for _ in range(per):
        t = rng.choice(_SIMPLE_TEMPLATES)
        text = t.format(p=rng.choice(terms))
        rows.append({"text": text, "label": "simple"})
    for _ in range(n - per):
        t = rng.choice(_COMPLEX_TEMPLATES)
        text = t.format(p=rng.choice(terms), p2=rng.choice(terms), n=rng.choice([8, 10, 12, 14, 16, 20]))
        rows.append({"text": text, "label": "complex"})
    rng.shuffle(rows)
    return rows


def split(rows: list[dict], val_frac: float = 0.2, seed: int = 7):
    rng = random.Random(seed)
    rows = list(rows)
    rng.shuffle(rows)
    k = int(len(rows) * (1 - val_frac))
    return rows[:k], rows[k:]
