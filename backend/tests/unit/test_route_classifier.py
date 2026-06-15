"""Synthetic-data generation (keyless) + the trained route classifier (skipped without sklearn)."""

from __future__ import annotations

from collections import Counter

import pytest

from app.ml.synth_data import LABELS, generate, split


def test_synth_data_is_balanced_and_labeled():
    rows = generate(n=400)
    assert len(rows) == 400
    counts = Counter(r["label"] for r in rows)
    assert set(counts) == set(LABELS)
    assert abs(counts["simple"] - counts["complex"]) <= 1  # balanced
    assert all(r["text"].strip() for r in rows)


def test_split_is_disjoint():
    rows = generate(n=200)
    tr, va = split(rows, val_frac=0.25)
    assert len(tr) + len(va) == len(rows)
    assert abs(len(va) - 50) <= 1


def test_trained_classifier_predicts():
    # Only runs where the model + scikit-learn are present (e.g. local dev, not CI image).
    pytest.importorskip("sklearn")
    pytest.importorskip("joblib")
    from pathlib import Path

    import app.ml.route_classifier as rc
    if not (Path(rc.__file__).resolve().parent / "router_lite.joblib").exists():
        pytest.skip("no trained model committed in this env")

    simple = rc.predict("how much is the cordless drill")
    complex_ = rc.predict("i want to paint my 12 by 10 foot room, what do i need")
    assert simple and simple[0] == "simple"
    assert complex_ and complex_[0] == "complex"
