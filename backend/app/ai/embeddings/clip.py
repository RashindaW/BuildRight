"""CLIP visual arm — a THIRD retrieval signal alongside lexical + text-vector.

A photo and a text query are embedded into the SAME CLIP space, so "the orange
cordless drill" can rank products by what they LOOK like, not just their words.
Product image embeddings live in `product_image_embeddings` (512-dim, ViT-B/32).

torch/open-clip are OPTIONAL (requirements-multimodal.txt), imported lazily and
guarded. Where they're absent (e.g. the deployed CPU image), every entry point
degrades to a no-op: `visual_search_products` returns [] and the hybrid fuser
simply runs lexical+vector — identical behaviour, suite stays green. The cosine
ranking math is pure and unit-tested without torch.
"""

from __future__ import annotations

import logging
import math
from typing import Sequence

logger = logging.getLogger("app.ai.embeddings.clip")

CLIP_MODEL_ID = "ViT-B-32/openai"
CLIP_DIM = 512

_clip_state = None  # None=unknown, False=unavailable, or a loaded (model, preprocess, tokenizer)


def _load_clip():
    """Load open-clip ViT-B/32 once; cache. Returns the bundle or None if torch absent."""
    global _clip_state
    if _clip_state is not None:
        return _clip_state or None
    try:
        import open_clip  # type: ignore
        import torch  # noqa: F401  type: ignore
        model, _, preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32", pretrained="openai"
        )
        model.eval()
        tokenizer = open_clip.get_tokenizer("ViT-B-32")
        _clip_state = (model, preprocess, tokenizer)
        logger.info("clip: loaded %s", CLIP_MODEL_ID)
        return _clip_state
    except Exception as e:  # ImportError, or torch DLL/init failure on this box
        logger.info("clip: unavailable (%s) — visual arm disabled", type(e).__name__)
        _clip_state = False
        return None


def embed_text(query: str) -> list[float] | None:
    """CLIP text embedding for a query, or None if CLIP is unavailable."""
    bundle = _load_clip()
    if bundle is None:
        return None
    import torch
    model, _, tokenizer = bundle
    with torch.no_grad():
        feats = model.encode_text(tokenizer([query]))
        feats = feats / feats.norm(dim=-1, keepdim=True)
    return feats[0].tolist()


def embed_image_bytes(data: bytes) -> list[float] | None:
    """CLIP image embedding for raw bytes, or None if CLIP/PIL is unavailable."""
    bundle = _load_clip()
    if bundle is None:
        return None
    try:
        import io
        import torch
        from PIL import Image
        model, preprocess, _ = bundle
        img = Image.open(io.BytesIO(data)).convert("RGB")
        with torch.no_grad():
            feats = model.encode_image(preprocess(img).unsqueeze(0))
            feats = feats / feats.norm(dim=-1, keepdim=True)
        return feats[0].tolist()
    except Exception as e:
        logger.warning("clip: image embed failed (%s)", type(e).__name__)
        return None


# ---- pure cosine ranking (unit-tested without torch) ----------------------

def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def rank_by_cosine(
    query_vec: Sequence[float],
    rows: Sequence[tuple[str, Sequence[float]]],
    k: int,
) -> list[str]:
    """Rank (slug, vector) rows by cosine vs the query; return the top-k slugs."""
    scored = [(slug, _cosine(query_vec, vec)) for slug, vec in rows if vec]
    scored.sort(key=lambda t: t[1], reverse=True)
    return [slug for slug, _ in scored[:k]]


# ---- entry points ---------------------------------------------------------

def visual_search_products(db, query: str, k: int = 12) -> list[str]:
    """Rank products by CLIP image similarity to the text query → product slugs.

    Returns [] (a no-op for the fuser) whenever CLIP is unavailable or no product
    images have been embedded yet — so the hybrid searcher is unaffected.
    """
    if not query.strip():
        return []
    qvec = embed_text(query)
    if qvec is None:
        return []
    from sqlalchemy import select
    from app.models.menu import MenuItem
    from app.models.product_image_embedding import ProductImageEmbedding

    rows = db.execute(
        select(MenuItem.slug, ProductImageEmbedding.embedding)
        .join(ProductImageEmbedding, ProductImageEmbedding.menu_item_id == MenuItem.id)
        .where(ProductImageEmbedding.embedding.is_not(None))
    ).all()
    if not rows:
        return []
    return rank_by_cosine(qvec, [(r[0], r[1]) for r in rows], k)


def index_product_images(db, *, only_missing: bool = True) -> int:
    """Embed each product's image into product_image_embeddings (CLIP). Returns the
    number embedded. No-op (returns 0) without CLIP. Runs on a torch host."""
    bundle = _load_clip()
    if bundle is None:
        logger.info("clip: index_product_images skipped — CLIP unavailable")
        return 0
    import hashlib
    import httpx
    from sqlalchemy import select
    from app.models.menu import MenuItem
    from app.models.product_image_embedding import ProductImageEmbedding

    existing = {
        e.menu_item_id: e
        for e in db.execute(select(ProductImageEmbedding)).scalars()
    }
    items = db.execute(
        select(MenuItem).where(MenuItem.image_url.is_not(None))
    ).scalars().all()
    n = 0
    for item in items:
        if only_missing and item.id in existing and existing[item.id].embedding:
            continue
        try:
            data = httpx.get(item.image_url, timeout=15, follow_redirects=True).content
        except Exception as e:
            logger.warning("clip: fetch failed for %s (%s)", item.slug, type(e).__name__)
            continue
        vec = embed_image_bytes(data)
        if vec is None:
            continue
        chash = hashlib.sha256((item.image_url or "").encode()).hexdigest()[:64]
        row = existing.get(item.id)
        if row is None:
            row = ProductImageEmbedding(menu_item_id=item.id)
            db.add(row)
        row.embedding = vec
        row.content_hash = chash
        row.model_id = CLIP_MODEL_ID
        n += 1
    db.commit()
    logger.info("clip: indexed %d product images", n)
    return n
