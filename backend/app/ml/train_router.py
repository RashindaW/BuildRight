"""Fine-tune a DistilBERT route classifier (simple vs complex) on synthetic data.

    pip install -r backend/ml/requirements-train.txt
    python -m app.ml.train_router

Pipeline: synthetic labeled data -> tokenize -> fine-tune DistilBERT (HF Transformers
+ PyTorch) -> evaluate on a held-out split AND against the heuristic router baseline
-> save the model + a committed metrics report. Offline; the deployed image never
needs torch.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger("app.ml.train")

_DIR = Path(__file__).resolve().parent
_MODEL_DIR = _DIR / "model"            # weights (gitignored)
_METRICS = _DIR / "metrics.json"       # committed
_REPORT = _DIR / "report.md"           # committed

MODEL_NAME = "distilbert-base-uncased"
MAX_LEN = 48
EPOCHS = 3
BATCH = 16
LR = 5e-5


def _heuristic_baseline(rows: list[dict]) -> float:
    """Accuracy of the keyword heuristic the live router uses today."""
    from app.ai.router import _COMPLEX_HINTS
    correct = 0
    for r in rows:
        pred = "complex" if any(h in r["text"].lower() for h in _COMPLEX_HINTS) else "simple"
        correct += pred == r["label"]
    return round(correct / len(rows), 4)


def _metrics(y_true: list[int], y_pred: list[int]) -> dict:
    n = len(y_true)
    acc = sum(int(a == b) for a, b in zip(y_true, y_pred)) / n
    # macro-F1 over the 2 classes
    f1s = []
    for c in (0, 1):
        tp = sum(1 for a, b in zip(y_true, y_pred) if a == c and b == c)
        fp = sum(1 for a, b in zip(y_true, y_pred) if a != c and b == c)
        fn = sum(1 for a, b in zip(y_true, y_pred) if a == c and b != c)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    return {"accuracy": round(acc, 4), "macro_f1": round(sum(f1s) / len(f1s), 4)}


def main() -> None:
    import torch
    from torch.utils.data import DataLoader, Dataset
    from transformers import (
        DistilBertForSequenceClassification,
        DistilBertTokenizerFast,
    )

    from app.ml.synth_data import LABEL2ID, LABELS, generate, split

    logging.basicConfig(level=logging.INFO)
    rows = generate()
    train_rows, val_rows = split(rows)
    logger.info("synthetic data: %d train / %d val", len(train_rows), len(val_rows))

    tok = DistilBertTokenizerFast.from_pretrained(MODEL_NAME)

    class DS(Dataset):
        def __init__(self, data):
            self.enc = tok([r["text"] for r in data], truncation=True, padding="max_length",
                           max_length=MAX_LEN, return_tensors="pt")
            self.labels = torch.tensor([LABEL2ID[r["label"]] for r in data])

        def __len__(self):
            return len(self.labels)

        def __getitem__(self, i):
            return {"input_ids": self.enc["input_ids"][i],
                    "attention_mask": self.enc["attention_mask"][i],
                    "labels": self.labels[i]}

    train_dl = DataLoader(DS(train_rows), batch_size=BATCH, shuffle=True)
    val_ds = DS(val_rows)
    val_dl = DataLoader(val_ds, batch_size=BATCH)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = DistilBertForSequenceClassification.from_pretrained(
        MODEL_NAME, num_labels=len(LABELS)).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=LR)

    for epoch in range(EPOCHS):
        model.train()
        total = 0.0
        for batch in train_dl:
            batch = {k: v.to(device) for k, v in batch.items()}
            opt.zero_grad()
            out = model(**batch)
            out.loss.backward()
            opt.step()
            total += out.loss.item()
        logger.info("epoch %d: train_loss=%.4f", epoch + 1, total / len(train_dl))

    # Evaluate the fine-tuned model on the held-out split.
    model.eval()
    y_true, y_pred = [], []
    with torch.no_grad():
        for batch in val_dl:
            labels = batch["labels"]
            ids = {k: v.to(device) for k, v in batch.items() if k != "labels"}
            preds = model(**ids).logits.argmax(-1).cpu().tolist()
            y_pred.extend(preds)
            y_true.extend(labels.tolist())

    ft = _metrics(y_true, y_pred)
    base_acc = _heuristic_baseline(val_rows)
    result = {
        "model": MODEL_NAME,
        "train_size": len(train_rows),
        "val_size": len(val_rows),
        "epochs": EPOCHS,
        "fine_tuned": ft,
        "heuristic_baseline_accuracy": base_acc,
        "labels": LABELS,
    }

    _MODEL_DIR.mkdir(exist_ok=True)
    model.save_pretrained(_MODEL_DIR)
    tok.save_pretrained(_MODEL_DIR)
    _METRICS.write_text(json.dumps(result, indent=2), encoding="utf-8")
    _REPORT.write_text(
        f"# Route classifier — fine-tuning report\n\n"
        f"Fine-tuned **{MODEL_NAME}** (HF Transformers + PyTorch) to classify a chat turn as "
        f"`simple` vs `complex` for the model router, on **{len(rows)} synthetic labeled** "
        f"examples grounded in the catalog vocabulary.\n\n"
        f"| Metric | Fine-tuned DistilBERT | Heuristic baseline |\n"
        f"|---|---|---|\n"
        f"| Accuracy | **{ft['accuracy']}** | {base_acc} |\n"
        f"| Macro-F1 | **{ft['macro_f1']}** | — |\n\n"
        f"- Train/val split: {len(train_rows)}/{len(val_rows)} · {EPOCHS} epochs · CPU-trainable.\n"
        f"- The live router stays cheap (heuristic + Haiku); this model is an offline upgrade "
        f"that `app/ml/route_classifier.py` can load with a graceful fallback.\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))
    print(f"\nSaved model -> {_MODEL_DIR}\nMetrics -> {_METRICS}\nReport -> {_REPORT}")


if __name__ == "__main__":
    main()
