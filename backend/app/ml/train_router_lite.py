"""Lightweight route classifier — TF-IDF + Logistic Regression (scikit-learn).

    python -m app.ml.train_router_lite

A dependency-light counterpart to train_router.py (DistilBERT). It runs ANYWHERE
scikit-learn installs (no torch/GPU), trains in seconds, and produces the same
committed artifacts: a saved model, metrics.json, and report.md — evaluated on a
held-out split and compared to the heuristic router the live app uses today.

This is what makes the fine-tuning result reproducible on this machine; the
DistilBERT script is the production-grade upgrade for a torch-capable host.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger("app.ml.train_lite")

_DIR = Path(__file__).resolve().parent
_MODEL = _DIR / "router_lite.joblib"   # small, committed
_METRICS = _DIR / "metrics.json"       # committed
_REPORT = _DIR / "report.md"           # committed


def _heuristic_baseline(rows: list[dict]) -> float:
    from app.ai.router import _COMPLEX_HINTS
    correct = sum(
        ("complex" if any(h in r["text"].lower() for h in _COMPLEX_HINTS) else "simple") == r["label"]
        for r in rows
    )
    return round(correct / len(rows), 4)


def main() -> None:
    import joblib
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, f1_score
    from sklearn.pipeline import Pipeline

    from app.ml.synth_data import generate, split

    logging.basicConfig(level=logging.INFO)
    rows = generate()
    train_rows, val_rows = split(rows)
    logger.info("synthetic data: %d train / %d val", len(train_rows), len(val_rows))

    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2)),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])
    pipe.fit([r["text"] for r in train_rows], [r["label"] for r in train_rows])

    y_true = [r["label"] for r in val_rows]
    y_pred = list(pipe.predict([r["text"] for r in val_rows]))
    ft = {
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
        "macro_f1": round(f1_score(y_true, y_pred, average="macro"), 4),
    }
    base_acc = _heuristic_baseline(val_rows)

    result = {
        "model": "tfidf+logreg (scikit-learn)",
        "alt_model_available": "distilbert-base-uncased (app/ml/train_router.py, torch host)",
        "train_size": len(train_rows),
        "val_size": len(val_rows),
        "fine_tuned": ft,
        "heuristic_baseline_accuracy": base_acc,
        "labels": ["simple", "complex"],
    }

    joblib.dump(pipe, _MODEL)
    _METRICS.write_text(json.dumps(result, indent=2), encoding="utf-8")
    _REPORT.write_text(
        "# Route classifier — training report\n\n"
        "Trained a classifier to label a chat turn `simple` vs `complex` for the model "
        f"router, on **{len(rows)} synthetic labeled** examples grounded in the catalog "
        "vocabulary (see `synth_data.py`).\n\n"
        f"| Metric | Trained classifier | Heuristic baseline |\n"
        f"|---|---|---|\n"
        f"| Accuracy | **{ft['accuracy']}** | {base_acc} |\n"
        f"| Macro-F1 | **{ft['macro_f1']}** | — |\n\n"
        f"- Model: TF-IDF + Logistic Regression (scikit-learn) — runs anywhere, trains in seconds.\n"
        f"- Production upgrade: **`train_router.py`** fine-tunes **DistilBERT** "
        "(HuggingFace Transformers + PyTorch) with the same data + report format, for a "
        "torch-capable host (Colab/Cloud Run GPU).\n"
        f"- Train/val split: {len(train_rows)}/{len(val_rows)}. The live router stays cheap "
        "(heuristic + Haiku); `route_classifier.py` can load this model with a graceful fallback.\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))
    print(f"\nSaved model -> {_MODEL}\nMetrics -> {_METRICS}\nReport -> {_REPORT}")


if __name__ == "__main__":
    main()
