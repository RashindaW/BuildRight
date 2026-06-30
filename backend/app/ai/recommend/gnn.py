"""Graph-neural recommender — item embeddings learned by propagating product content
features over the user co-purchase graph (an SGC / LightGCN-style graph convolution).

Two-stage by design, mirroring the project's optional-dependency pattern:

  * BUILD (offline, at seed time): `build_graph_embeddings` does K rounds of symmetric-
    normalized neighbourhood aggregation over the co-purchase graph, seeded with the 384-d
    text embeddings as node features, and writes the result to `product_graph_embeddings`.
    It uses **NumPy only** (already a dependency), so it runs everywhere — including the
    deployed CPU image and this box (where torch is broken). A trainable PyTorch-Geometric
    LightGCN could replace it on a torch host and write to the same table.

  * SERVE (online, per request): `graph_recommend` ranks candidates by cosine over the
    stored graph vectors — **torch-free** — and degrades to the co-occurrence / content
    recommenders when the table is empty (no graph built yet).
"""

from __future__ import annotations

import logging
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.menu import MenuItem
from app.models.order import OrderItem
from app.models.product_embedding import ProductEmbedding
from app.models.product_graph_embedding import ProductGraphEmbedding

logger = logging.getLogger("app.ai.recommend.gnn")

_MODEL_ID = "graph-sgc-v1"


def build_graph_embeddings(db: Session, *, layers: int = 2, model_id: str = _MODEL_ID) -> int:
    """Propagate content features over the co-purchase graph and persist the result.

    Returns the number of graph vectors written. No-op (0) if no product embeddings exist.
    """
    import numpy as np

    feats = {
        mid: emb
        for mid, emb in db.execute(
            select(ProductEmbedding.menu_item_id, ProductEmbedding.embedding)
        ).all()
        if emb is not None
    }
    if not feats:
        logger.info("build_graph_embeddings: no product embeddings yet — skipping")
        return 0

    ids = list(feats.keys())
    idx = {mid: i for i, mid in enumerate(ids)}
    n = len(ids)
    X = np.asarray([feats[mid] for mid in ids], dtype=np.float32)

    # Co-purchase edges: items appearing together in the same order (weighted by count).
    baskets: dict[str, set[int]] = {}
    for oid, mid in db.execute(select(OrderItem.order_id, OrderItem.menu_item_id)).all():
        if mid in idx:
            baskets.setdefault(oid, set()).add(idx[mid])

    adj: list[dict[int, float]] = [defaultdict(float) for _ in range(n)]
    for members in baskets.values():
        members = list(members)
        for a in range(len(members)):
            for b in range(a + 1, len(members)):
                i, j = members[a], members[b]
                adj[i][j] += 1.0
                adj[j][i] += 1.0

    # Symmetric-normalized propagation with self-loops; final = mean over layers (LightGCN).
    deg = np.asarray([1.0 + sum(adj[i].values()) for i in range(n)], dtype=np.float32)
    inv_sqrt = 1.0 / np.sqrt(deg)

    H = X.copy()
    acc = X.copy()
    for _ in range(layers):
        new_h = np.zeros_like(H)
        for i in range(n):
            isq_i = inv_sqrt[i]
            s = (isq_i * isq_i) * H[i]
            for j, w in adj[i].items():
                s = s + (w * isq_i * inv_sqrt[j]) * H[j]
            new_h[i] = s
        acc = acc + new_h
        H = new_h
    Z = acc / (layers + 1)
    norms = np.linalg.norm(Z, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    Z = Z / norms

    existing = {
        e.menu_item_id: e for e in db.execute(select(ProductGraphEmbedding)).scalars()
    }
    for mid, i in idx.items():
        vec = Z[i].tolist()
        row = existing.get(mid)
        if row is None:
            db.add(ProductGraphEmbedding(menu_item_id=mid, embedding=vec, model_id=model_id))
        else:
            row.embedding = vec
            row.model_id = model_id
    db.commit()
    logger.info("build_graph_embeddings: wrote %d graph vectors (%d layers)", n, layers)
    return n


def graph_recommend(db: Session, item_ref: str, k: int = 5) -> list[dict]:
    """Recommend items via cosine over the graph embeddings. Torch-free.

    Returns [] when no graph has been built or the anchor has no vector — the caller then
    falls back to the co-occurrence / content recommenders.
    """
    import numpy as np

    from app.services.recommender_service import _resolve, _serialize

    anchor = _resolve(db, item_ref)
    if anchor is None:
        return []

    vecs = {
        mid: emb
        for mid, emb in db.execute(
            select(ProductGraphEmbedding.menu_item_id, ProductGraphEmbedding.embedding)
        ).all()
        if emb is not None
    }
    anchor_vec = vecs.get(anchor.id)
    if anchor_vec is None:
        return []

    av = np.asarray(anchor_vec, dtype=np.float32)
    a_norm = float(np.linalg.norm(av)) or 1.0
    available = set(
        db.execute(
            select(MenuItem.id).where(MenuItem.is_available.is_(True), MenuItem.stock_qty > 0)
        ).scalars()
    )

    scored: list[tuple[str, float]] = []
    for mid, emb in vecs.items():
        if mid == anchor.id or mid not in available:
            continue
        cv = np.asarray(emb, dtype=np.float32)
        denom = a_norm * (float(np.linalg.norm(cv)) or 1.0)
        scored.append((mid, float(np.dot(av, cv) / denom)))

    scored.sort(key=lambda t: t[1], reverse=True)
    top = scored[:k]
    if not top:
        return []

    items = {
        it.id: it
        for it in db.execute(select(MenuItem).where(MenuItem.id.in_([m for m, _ in top]))).scalars()
    }
    out = []
    for mid, sim in top:
        it = items.get(mid)
        if it is not None:
            out.append(_serialize(it, score=round(sim, 4), reason="often used together (graph)"))
    return out
