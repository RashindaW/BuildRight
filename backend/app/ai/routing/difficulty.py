"""Learned difficulty head — P(the cheap model handles this turn well).

A logistic regression over [hash-embedding ⊕ engineered scalars], trained offline by
scripts/train_router.py (pure NumPy — no sklearn) and served here from a committed JSON
artifact. Inference is NumPy-only and adds ~0ms to routing (vs ~300ms for the old
LLM-classifier round-trip).

The embedding is ALWAYS the deterministic HashEmbeddingProvider — never the main
provider — so the train-time and serve-time feature spaces are identical on every host
(fastembed availability varies; the hash space does not).
"""

from __future__ import annotations

import json
import logging
import math
import re
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger("app.ai.routing")

_ARTIFACT = Path(__file__).with_name("artifacts") / "router_head_v1.json"

# Engineered scalars appended to the embedding. Mirrors the old router's hints so the
# learned head starts from at least heuristic-grade signal.
_COMPLEX_CUES = (
    # NOTE: deliberately narrower than a "price question" cue — "how much is X?" is a
    # simple lookup; "how much paint do I need" is planning (caught by need/for + digits).
    "repair", "renovat", "build", "install", "project", "how many",
    "sq ft", "square feet", "square foot", "deck", "fence", "drywall", "tile",
    "laminate", "paint my", "difference between", " vs ", "versus", "compare",
    "which should", "plan", "estimate", "do i need",
)
_DIGITS_RE = re.compile(r"\d")


def features_for(question: str, has_image: bool = False, turn_index: int = 0) -> list[float]:
    q = (question or "").strip()
    ql = q.lower()
    emb = _hash_provider().embed_query(q)
    scalars = [
        min(len(q), 400) / 400.0,
        min(len(q.split()), 60) / 60.0,
        min(len(_DIGITS_RE.findall(q)), 12) / 12.0,
        float(any(c in ql for c in _COMPLEX_CUES)),
        float("?" in q),
        float(has_image),
        min(turn_index, 10) / 10.0,
    ]
    return list(emb) + scalars


@lru_cache(maxsize=1)
def _hash_provider():
    from app.ai.embeddings.provider import HashEmbeddingProvider
    return HashEmbeddingProvider()


@lru_cache(maxsize=1)
def _load_head() -> dict | None:
    try:
        return json.loads(_ARTIFACT.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("router head artifact missing (%s) — difficulty defaults to cues", _ARTIFACT)
        return None
    except Exception:  # noqa: BLE001
        logger.exception("router head artifact unreadable — difficulty defaults to cues")
        return None


def p_cheap_ok(question: str, has_image: bool = False, turn_index: int = 0) -> float:
    """P(cheap model succeeds). Falls back to a cue heuristic without an artifact."""
    head = _load_head()
    x = features_for(question, has_image, turn_index)
    if head is None:
        return 0.25 if x[-4] or has_image else 0.85  # complex-cue / image → hard
    w, b = head["weights"], head["bias"]
    z = b + sum(wi * xi for wi, xi in zip(w, x))
    return 1.0 / (1.0 + math.exp(-z))
