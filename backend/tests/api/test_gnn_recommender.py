"""GNN/graph recommender: deterministic build over synthetic interactions, torch-free
serving, idempotency, and graceful degradation when no graph exists."""

from __future__ import annotations

import os
import tempfile

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401 - register all models on the metadata
from app.ai.embeddings.indexer import embed_products
from app.ai.embeddings.provider import get_embedding_provider
from app.ai.recommend.gnn import build_graph_embeddings, graph_recommend
from app.core.db import SessionLocal
from app.models.base import Base
from app.models.menu import MenuItem
from app.seed.seed import seed_menu
from app.seed.seed_interactions import seed_interactions


def test_gnn_build_and_recommend_isolated():
    """Build a real graph in an isolated DB and verify serving — no torch involved."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}")
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        Base.metadata.create_all(engine)
        seed_menu(db)
        embed_products(db, get_embedding_provider())  # node features
        n_orders = seed_interactions(db, users=25)
        assert n_orders > 0
        assert seed_interactions(db, users=25) == 0  # idempotent

        n_vecs = build_graph_embeddings(db)
        assert n_vecs > 0
        assert build_graph_embeddings(db) == n_vecs  # deterministic/idempotent rebuild

        item = db.execute(
            select(MenuItem).where(MenuItem.is_available.is_(True)).limit(1)
        ).scalar_one()
        recs = graph_recommend(db, item.slug, k=5)
        assert isinstance(recs, list)
        for r in recs:
            assert r["slug"] != item.slug
            assert "score" in r and "name" in r

        # Recall@k eval over held-out co-purchases — the graph model is measured, not assumed.
        from app.ai.eval.recommender_eval import evaluate

        metrics = evaluate(db, k=5, sample=120)
        assert metrics["pairs"] > 0
        assert 0.0 <= metrics["graph_recall"] <= 1.0
        assert 0.0 <= metrics["cooccurrence_recall"] <= 1.0
    finally:
        db.close()
        engine.dispose()
        os.unlink(path)


def test_graph_recommend_degrades_without_graph(seeded_item):
    """With no graph built (the shared test DB), serving returns [] so the caller falls
    back to the co-occurrence / content recommenders."""
    db = SessionLocal()
    try:
        assert graph_recommend(db, seeded_item["slug"]) == []
    finally:
        db.close()


def test_item_graph_endpoint(client, seeded_item):
    """The /graph viz endpoint returns the anchor + (possibly empty) neighbour list."""
    r = client.get(f"/api/v1/menu/{seeded_item['slug']}/graph")
    assert r.status_code == 200
    body = r.json()
    assert body["anchor"]["slug"] == seeded_item["slug"]
    assert isinstance(body["neighbors"], list)
