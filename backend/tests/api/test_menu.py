from __future__ import annotations


def test_list_menu_public(client):
    r = client.get("/api/v1/menu")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 15
    assert all("price" in i and "price_cents" in i for i in body["items"])


def test_price_formatting_matches_cents(client):
    r = client.get("/api/v1/menu/classic-latte")
    assert r.status_code == 200
    item = r.json()
    assert item["price_cents"] == 450
    assert f"${item['price']:.2f}" == "$4.50"


def test_filter_by_dietary_vegan(client):
    r = client.get("/api/v1/menu", params={"dietary": ["vegan"]})
    assert r.status_code == 200
    assert all("vegan" in i["dietary_tags"] for i in r.json()["items"])


def test_filter_by_category(client):
    r = client.get("/api/v1/menu", params={"category": "drink"})
    assert r.status_code == 200
    assert all(i["category"] == "drink" for i in r.json()["items"])


def test_search_query(client):
    r = client.get("/api/v1/menu", params={"q": "caesar"})
    assert r.status_code == 200
    names = [i["name"] for i in r.json()["items"]]
    assert any("Caesar" in n for n in names)


def test_get_unknown_item_404(client):
    assert client.get("/api/v1/menu/does-not-exist").status_code == 404


def test_categories_listed(client):
    r = client.get("/api/v1/menu/categories")
    assert r.status_code == 200
    slugs = {c["slug"] for c in r.json()}
    assert {"salad", "drink", "dessert"}.issubset(slugs)
