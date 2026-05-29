"""Download matching food photos for each menu item.

Source: LoremFlickr (https://loremflickr.com) — Creative Commons Flickr images
by keyword, no API key. Saves to frontend/public/img/menu/<slug>.jpg, which is
gitignored (images are not redistributed in the repo).

Usage:  python scripts/fetch_images.py
Idempotent: skips files that already exist and look like valid JPEGs.
"""

from __future__ import annotations

import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend" / "public" / "img" / "menu"
OUT.mkdir(parents=True, exist_ok=True)

# Curated keyword queries per item slug for the best-matching photo.
QUERIES: dict[str, str] = {
    "caesar-salad": "caesar,salad",
    "vegan-buddha-bowl": "buddha,bowl,quinoa",
    "chicken-cobb-salad": "cobb,salad",
    "turkey-club": "club,sandwich",
    "vegan-avocado-wrap": "wrap,avocado",
    "gf-veggie-panini": "panini,sandwich",
    "margherita-pasta": "pasta,penne",
    "shrimp-linguine": "linguine,shrimp",
    "classic-latte": "latte,coffee",
    "iced-oat-latte": "iced,coffee",
    "fresh-lemonade": "lemonade",
    "mango-smoothie": "mango,smoothie",
    "cappuccino": "cappuccino",
    "green-tea": "green,tea",
    "orange-juice": "orange,juice",
    "chocolate-lava-cake": "chocolate,cake",
    "almond-croissant": "croissant",
    "flourless-chocolate-torte": "chocolate,torte",
    "new-york-cheesecake": "cheesecake",
    "vegan-chocolate-mousse": "chocolate,mousse",
    "tomato-bruschetta": "bruschetta",
    "soup-of-the-day": "soup,bowl",
    "crispy-calamari": "calamari,fried",
    "margherita-pizza": "pizza,margherita",
    "pepperoni-pizza": "pizza,pepperoni",
    "vegan-garden-pizza": "pizza,vegetables",
    "grilled-salmon": "salmon,grilled",
    "ribeye-steak": "steak,ribeye",
    "mushroom-risotto": "risotto,mushroom",
    "eggplant-parmesan": "eggplant,parmesan",
    "sweet-potato-fries": "sweet,potato,fries",
    "garlic-bread": "garlic,bread",
    "house-side-salad": "green,salad",
    "kids-mac-and-cheese": "macaroni,cheese",
    "kids-chicken-tenders": "chicken,tenders",
}

UA = {"User-Agent": "Mozilla/5.0 (cutdry image fetcher)"}
MIN_BYTES = 3000


def _valid_jpeg(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < MIN_BYTES:
        return False
    with open(path, "rb") as f:
        return f.read(2) == b"\xff\xd8"  # JPEG magic


def fetch(slug: str, query: str) -> bool:
    dest = OUT / f"{slug}.jpg"
    if _valid_jpeg(dest):
        return True
    url = f"https://loremflickr.com/600/400/{query}"
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=20) as r:
                data = r.read()
            if len(data) >= MIN_BYTES and data[:2] == b"\xff\xd8":
                dest.write_bytes(data)
                return True
        except Exception:
            pass
        time.sleep(1.5)
    return False


def main() -> int:
    ok, fail = [], []
    for slug, query in QUERIES.items():
        if fetch(slug, query):
            ok.append(slug)
            print(f"  [ok]   {slug}.jpg")
        else:
            fail.append(slug)
            print(f"  [FAIL] {slug}")
    print(f"\nDownloaded {len(ok)}/{len(QUERIES)} -> {OUT}")
    if fail:
        print("Failed:", ", ".join(fail))
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())
