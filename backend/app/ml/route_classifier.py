"""Optional trained route classifier for the model router.

predict(text) -> ("simple"|"complex", confidence) or None.

Resolution order: a fine-tuned DistilBERT (if present + torch loads) → the
committed TF-IDF/LogReg model (if present + scikit-learn installed) → None.
Everything is lazy + best-effort: in the deployed image (no torch/sklearn) this
returns None and the router falls back to its heuristic, so the hot path is never
at risk. This is the integration point that lets the offline-trained model serve
predictions wherever its deps are available.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("app.ml.route_classifier")

_DIR = Path(__file__).resolve().parent
_LITE_MODEL = _DIR / "router_lite.joblib"
_BERT_DIR = _DIR / "model"

_backend = None          # "bert" | "lite" | "none"
_obj = None              # loaded model/pipeline


def _load() -> str:
    global _backend, _obj
    if _backend is not None:
        return _backend
    # 1) DistilBERT (production upgrade) if torch loads on this host.
    if _BERT_DIR.exists():
        try:
            import torch  # noqa: F401
            from transformers import (
                DistilBertForSequenceClassification,
                DistilBertTokenizerFast,
            )
            _obj = (
                DistilBertTokenizerFast.from_pretrained(_BERT_DIR),
                DistilBertForSequenceClassification.from_pretrained(_BERT_DIR),
            )
            _backend = "bert"
            return _backend
        except Exception:  # noqa: BLE001 - torch unavailable/broken → try lite
            logger.info("distilbert classifier unavailable; trying lite model")
    # 2) Lightweight scikit-learn model (runs anywhere sklearn installs).
    if _LITE_MODEL.exists():
        try:
            import joblib
            _obj = joblib.load(_LITE_MODEL)
            _backend = "lite"
            return _backend
        except Exception:  # noqa: BLE001
            logger.info("lite classifier unavailable")
    _backend = "none"
    return _backend


def predict(text: str) -> tuple[str, float] | None:
    """Return (label, confidence) or None when no trained model/deps are present."""
    backend = _load()
    if backend == "lite":
        try:
            proba = _obj.predict_proba([text])[0]
            classes = list(_obj.classes_)
            i = int(proba.argmax())
            return classes[i], float(proba[i])
        except Exception:  # noqa: BLE001
            return None
    if backend == "bert":
        try:
            import torch
            tok, model = _obj
            enc = tok(text, truncation=True, padding=True, max_length=48, return_tensors="pt")
            with torch.no_grad():
                probs = model(**enc).logits.softmax(-1)[0]
            labels = ["simple", "complex"]
            i = int(probs.argmax())
            return labels[i], float(probs[i])
        except Exception:  # noqa: BLE001
            return None
    return None
