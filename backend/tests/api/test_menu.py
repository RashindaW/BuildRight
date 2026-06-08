from __future__ import annotations


def test_list_menu_public(client):
    r = client.get("/api/v1/menu")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 15
    assert all("price" in i and "price_cents" in i for i in body["items"])


def test_price_formatting_matches_cents(client, seeded_item):
    r = client.get(f"/api/v1/menu/{seeded_item['slug']}")
    assert r.status_code == 200
    item = r.json()
    assert item["price_cents"] == seeded_item["price_cents"]
    # price float is reconstructed from integer cents -> formats back byte-identical
    assert f"${item['price']:.2f}" == f"${seeded_item['price_cents'] / 100:.2f}"


def test_filter_by_dietary_vegan(client):
    r = client.get("/api/v1/menu", params={"dietary": ["vegan"]})
    assert r.status_code == 200
    assert all("vegan" in i["dietary_tags"] for i in r.json()["items"])


def test_filter_by_category(client):
    r = client.get("/api/v1/menu", params={"category": "drink"})
    assert r.status_code == 200
    assert all(i["category"] == "drink" for i in r.json()["items"])


def test_search_query(client, seeded_item):
    # Search for a clean alphabetic word from a real seeded item's name and expect
    # it back. Punctuation-free + len>=4 so the lexical tokenizer matches cleanly.
    words = [w for w in seeded_item["name"].split() if w.isalpha() and len(w) >= 4]
    term = words[0] if words else seeded_item["name"].split()[0]
    r = client.get("/api/v1/menu", params={"q": term})
    assert r.status_code == 200
    names = [i["name"] for i in r.json()["items"]]
    assert any(term.lower() in n.lower() for n in names)


def test_get_unknown_item_404(client):
    assert client.get("/api/v1/menu/does-not-exist").status_code == 404


def test_categories_listed(client, seeded_item):
    r = client.get("/api/v1/menu/categories")
    assert r.status_code == 200
    slugs = {c["slug"] for c in r.json()}
    assert slugs, "no categories returned"
    # The seeded item's own category must be present in the category listing.
    assert seeded_item["category"] in slugs
