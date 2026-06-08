"""Golden validation set for the cafe assistant.

Runs 10 fixed queries through answer_customer_query and asserts substring
expectations on each response. Exit code 0 on full pass, 1 on any failure.

Usage:
    python golden_tests.py

Schema for each test:
    {
        "id":               unique slug,
        "query":            the customer input,
        "must_contain_any": at least one substring must appear in the response,
        "must_contain_all": every substring must appear,
        "must_not_contain": none of these substrings may appear,
        "must_contain_n_of": (list, n) — at least n items from the list must appear,
        "validates":        human note on what this case proves
    }
All substring checks are case-insensitive.
"""

from __future__ import annotations

import os
import sys

from assistant import answer_customer_query
from menu_data_legacy_cafe import MENU_DATA


# ============================================================
# Dynamic expected values pulled from MENU_DATA
# ============================================================

def _by_tag(tag: str) -> list[dict]:
    return [it for it in MENU_DATA if tag in it["dietary_tags"]]


VEGAN_ITEMS = _by_tag("vegan")
VEGAN_NAMES = [it["name"] for it in VEGAN_ITEMS]

LATTE_ITEM = next(it for it in MENU_DATA if it["id"] == "classic-latte")
LATTE_PRICE_STR = f"${LATTE_ITEM['price']:.2f}"  # e.g. "$4.50"

CAESAR_ITEM = next(it for it in MENU_DATA if it["id"] == "caesar-salad")
CAESAR_PRICE_STR = f"${CAESAR_ITEM['price']:.2f}"  # e.g. "$11.50"

GF_LUNCH_UNDER_15 = [
    it for it in MENU_DATA
    if "gluten-free" in it["dietary_tags"]
    and it["price"] <= 15.0
    and it["category"] in {"salad", "sandwich", "pasta"}
]
GF_LUNCH_UNDER_15_NAMES = [it["name"] for it in GF_LUNCH_UNDER_15]

DAIRY_FREE_DRINKS = [
    it for it in MENU_DATA
    if it["category"] == "drink" and "dairy-free" in it["dietary_tags"]
]
DAIRY_FREE_DRINK_NAMES = [it["name"] for it in DAIRY_FREE_DRINKS]

NUT_ITEMS = _by_tag("contains-nuts")
NUT_NAMES = [it["name"] for it in NUT_ITEMS]

ALL_NAMES = [it["name"] for it in MENU_DATA]

# Items that match "cold and sweet" semantically
COLD_AND_SWEET_NAMES = [
    "Fresh Lemonade",
    "Mango Smoothie",
    "Iced Oat Milk Latte",
    "Chocolate Lava Cake",
    "Almond Croissant",
    "Flourless Chocolate Torte",
]


# ============================================================
# The 10 golden cases
# ============================================================

TESTS = [
    {
        "id": "G01-caesar-salad-confirm",
        "query": "do you have a caesar salad?",
        "must_contain_any": ["caesar"],
        "must_contain_all": [CAESAR_PRICE_STR],
        "validates": "Direct lookup + Rule 2 (real price stated)",
    },
    {
        "id": "G02-vegan-filter",
        "query": "what's vegan?",
        "must_contain_n_of": (VEGAN_NAMES, len(VEGAN_NAMES)),
        "validates": "Dietary short-circuit + Rule 1 (only real items, all vegan items listed)",
    },
    {
        "id": "G03-latte-price",
        "query": "how much is the classic latte?",
        "must_contain_all": [LATTE_PRICE_STR],
        "validates": "Rule 2 positive case (exact menu price stated)",
    },
    {
        "id": "G04-sushi-apology",
        "query": "do you sell sushi?",
        "must_contain_any": [
            "sorry", "don't", "do not", "not currently",
            "not on our menu", "not offer", "unfortunately",
        ],
        "must_not_contain": ["sushi for $", "sushi is $", "sushi: $", "sushi at $"],
        "validates": "Rule 3 apology + Rule 1 (no invented sushi item)",
    },
    {
        "id": "G05-burger-50-anti-validation",
        "query": "is the burger $50?",
        "must_contain_any": [
            "sorry", "don't", "do not",
            "not on", "not currently", "not offer",
        ],
        "must_not_contain": ["$50", "50 dollars", "fifty dollars"],
        "validates": "CRITICAL: Rule 2 anti-validation + Rule 3 (no price repetition, apology)",
    },
    {
        "id": "G06-cold-and-sweet",
        "query": "something cold and sweet",
        "must_contain_any": COLD_AND_SWEET_NAMES,
        "validates": "Inexact keyword retrieval surfaces relevant items",
    },
    {
        "id": "G07-gf-lunch-under-15",
        "query": "a gluten-free lunch under $15",
        "must_contain_any": GF_LUNCH_UNDER_15_NAMES,
        "validates": "LLM multi-intent filtering (GF tag + price + lunch category)",
    },
    {
        "id": "G08-dairy-free-drinks",
        "query": "what drinks are dairy-free?",
        "must_contain_any": DAIRY_FREE_DRINK_NAMES,
        "validates": "Dietary short-circuit + LLM category filter",
    },
    {
        "id": "G09-browse-menu",
        "query": "what's on the menu?",
        "must_contain_n_of": (ALL_NAMES, 3),
        "validates": "Generic-browse short-circuit returns full menu",
    },
    {
        "id": "G10-nut-items",
        "query": "do you have anything with nuts?",
        "must_contain_any": NUT_NAMES,
        "validates": "Allergen surfacing (contains-nuts tag)",
    },
]


# ============================================================
# Test runner
# ============================================================

def _check(test: dict, response: str) -> str | None:
    """Return None on pass, or a one-line failure reason."""
    response_lower = response.lower()

    if "must_contain_all" in test:
        for needle in test["must_contain_all"]:
            if needle.lower() not in response_lower:
                return f"missing required substring '{needle}'"

    if "must_contain_any" in test:
        if not any(n.lower() in response_lower for n in test["must_contain_any"]):
            return (
                f"none of these substrings appeared (need at least one): "
                f"{test['must_contain_any']}"
            )

    if "must_not_contain" in test:
        for needle in test["must_not_contain"]:
            if needle.lower() in response_lower:
                return f"forbidden substring '{needle}' appeared"

    if "must_contain_n_of" in test:
        needles, min_count = test["must_contain_n_of"]
        found = [n for n in needles if n.lower() in response_lower]
        if len(found) < min_count:
            return (
                f"only {len(found)}/{min_count} required items appeared "
                f"(found: {found})"
            )

    return None


def _truncate(text: str, limit: int = 240) -> str:
    text = text.replace("\n", " ").strip()
    return text if len(text) <= limit else text[:limit] + "..."


def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY environment variable is not set.", file=sys.stderr)
        return 2

    print(f"Running {len(TESTS)} golden tests against answer_customer_query...\n")

    passed = 0
    failed_ids: list[str] = []

    for t in TESTS:
        try:
            response = answer_customer_query(t["query"])
        except Exception as e:
            failed_ids.append(t["id"])
            print(f"[FAIL] {t['id']} — raised {type(e).__name__}: {e}")
            print()
            continue

        failure = _check(t, response)
        if failure is None:
            passed += 1
            print(f"[PASS] {t['id']}")
        else:
            failed_ids.append(t["id"])
            print(f"[FAIL] {t['id']}")
            print(f"       Query:    {t['query']}")
            print(f"       Failure:  {failure}")
            print(f"       Response: {_truncate(response)}")
            print()

    print()
    print(f"Result: {passed}/{len(TESTS)} passed.")
    if failed_ids:
        print(f"Failed: {', '.join(failed_ids)}")
    return 0 if passed == len(TESTS) else 1


if __name__ == "__main__":
    sys.exit(main())
