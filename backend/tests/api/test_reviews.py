"""Product reviews: create, list, aggregate on the item, dedupe, validation."""

from __future__ import annotations


def test_review_create_list_and_aggregate(customer_client, seeded_item):
    slug = seeded_item["slug"]

    r = customer_client.post(
        f"/api/v1/menu/{slug}/reviews",
        json={"rating": 5, "comment": "Great tool, works perfectly!", "author_name": "Tester"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["rating"] == 5
    assert body["sentiment"] == "positive"

    listed = customer_client.get(f"/api/v1/menu/{slug}/reviews").json()
    assert listed["total"] >= 1
    assert any(rv["comment"] == "Great tool, works perfectly!" for rv in listed["items"])

    item = customer_client.get(f"/api/v1/menu/{slug}").json()
    assert item["rating_count"] >= 1
    assert item["rating_avg"] is not None

    # One review per user per product.
    dup = customer_client.post(f"/api/v1/menu/{slug}/reviews", json={"rating": 3})
    assert dup.status_code == 409


def test_review_summary_endpoint(customer_client, seeded_item):
    slug = seeded_item["slug"]
    summary = customer_client.get(f"/api/v1/menu/{slug}/review-summary").json()
    assert "count" in summary and "summary" in summary


def test_review_rating_must_be_valid(customer_client, seeded_item):
    r = customer_client.post(f"/api/v1/menu/{seeded_item['slug']}/reviews", json={"rating": 9})
    assert r.status_code == 422


def test_review_negative_sentiment(customer_client, menu_items):
    # Use a different item than the one rated above, to avoid the per-user dedupe.
    slug = menu_items[1]["slug"]
    r = customer_client.post(f"/api/v1/menu/{slug}/reviews", json={"rating": 1, "comment": "Broke quickly."})
    assert r.status_code == 200, r.text
    assert r.json()["sentiment"] == "negative"
