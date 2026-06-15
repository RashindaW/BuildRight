"""Offline ML training (NOT shipped to the live app / HF image).

A fine-tuned route classifier: synthetic labeled data -> DistilBERT (HF Transformers
+ PyTorch) -> evaluation vs the heuristic router. Demonstrates fine-tuning, synthetic
data generation, embeddings/transformers, and rigorous evaluation. Heavy deps live in
requirements-train.txt and are never installed into the deployed image.
"""
