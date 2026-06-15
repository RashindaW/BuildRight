# Route classifier — training report

Trained a classifier to label a chat turn `simple` vs `complex` for the model router, on **1600 synthetic labeled** examples grounded in the catalog vocabulary (see `synth_data.py`).

| Metric | Trained classifier | Heuristic baseline |
|---|---|---|
| Accuracy | **1.0** | 0.7844 |
| Macro-F1 | **1.0** | — |

- Model: TF-IDF + Logistic Regression (scikit-learn) — runs anywhere, trains in seconds.
- Production upgrade: **`train_router.py`** fine-tunes **DistilBERT** (HuggingFace Transformers + PyTorch) with the same data + report format, for a torch-capable host (Colab/Cloud Run GPU).
- Train/val split: 1280/320. The live router stays cheap (heuristic + Haiku); `route_classifier.py` can load this model with a graceful fallback.
