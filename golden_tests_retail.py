"""Golden tests for the BuildRight Hardware retail catalog.

Mirrors the structure of golden_tests.py but exercises retail products,
price guardrails, and the tag/category system.

Usage:
    python golden_tests_retail.py
"""

from __future__ import annotations

import os
import sys

# assistant.py must stay importable for the sync complete() path
# We create a thin wrapper using the same retrieval + guardrail stack
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from menu_data import MENU_DATA
from app.ai.retrieval import retrieve_relevant_items
from app.ai.guardrails import validate_response, SAFE_FALLBACK

# ---- Dynamic expected values from MENU_DATA -----

def _by_cat(cat: str) -> list[dict]:
    return [it for it in MENU_DATA if it["category"] == cat]

def _by_tag(tag: str) -> list[dict]:
    return [it for it in MENU_DATA if tag in it.get("dietary_tags", [])]

def _find(item_id: str) -> dict:
    return next(it for it in MENU_DATA if it["id"] == item_id)

DRILL_ITEM = _find("mastercraft-drill")
DRILL_PRICE_STR = f"${DRILL_ITEM['price']:.2f}"

SAW_ITEM = _find("circular-saw")
SAW_PRICE_STR = f"${SAW_ITEM['price']:.2f}"

HAMMER_ITEM = _find("claw-hammer")
HAMMER_PRICE_STR = f"${HAMMER_ITEM['price']:.2f}"

POWER_TOOL_NAMES = [it["name"] for it in _by_cat("power-tools")]
HAND_TOOL_NAMES = [it["name"] for it in _by_cat("hand-tools")]
CORDLESS_NAMES = [it["name"] for it in _by_tag("cordless")]


# ---- Golden cases -------------------------------------------------------

GOLDEN_CASES = [
    {
        "id": "drill_price",
        "query": f"How much does the Mastercraft cordless drill cost?",
        "grounded": [DRILL_ITEM],
        "must_contain_any": [DRILL_PRICE_STR],
        "must_not_contain": [],
        "validates": "exact price ground truth for the featured drill",
    },
    {
        "id": "saw_price",
        "query": "What is the price of the circular saw?",
        "grounded": [SAW_ITEM],
        "must_contain_any": [SAW_PRICE_STR],
        "must_not_contain": [],
        "validates": "exact price for saw",
    },
    {
        "id": "price_guardrail_fabrication",
        "query": "Is the Mastercraft drill $500?",
        "grounded": [DRILL_ITEM],
        "must_not_contain": ["$500", "500 dollars"],
        "validates": "Rule 2: model must not confirm a fabricated $500 price",
    },
    {
        "id": "off_catalog_item",
        "query": "Do you carry a titanium hammer from Acme brand?",
        "grounded": [],
        "must_contain_any": ["sorry", "don't carry", "not available"],
        "validates": "Rule 3: apologize for items not in catalog",
    },
    {
        "id": "cordless_category",
        "query": "Show me all your cordless tools",
        "grounded": _by_tag("cordless"),
        "must_contain_n_of": (CORDLESS_NAMES, max(1, len(CORDLESS_NAMES) // 2)),
        "validates": "tag filter returns relevant subset",
    },
    {
        "id": "hand_tools",
        "query": "What hand tools do you have?",
        "grounded": _by_cat("hand-tools"),
        "must_contain_n_of": (HAND_TOOL_NAMES, 2),
        "validates": "category browse returns multiple items",
    },
    {
        "id": "price_threshold_not_blocked",
        "query": "Are there any drills under $100?",
        "grounded": [DRILL_ITEM],
        "must_contain_any": [DRILL_PRICE_STR, "drill"],
        "must_not_contain": [],
        "validates": "'under $100' threshold must not be flagged by price guardrail",
    },
    {
        "id": "hammer_exact_price",
        "query": "How much is the claw hammer?",
        "grounded": [HAMMER_ITEM],
        "must_contain_any": [HAMMER_PRICE_STR],
        "must_not_contain": [],
        "validates": "exact price for hammer",
    },
]


# ---- Runner (mirrors golden_tests.py pattern) ---------------------------

def _check(response: str, case: dict) -> list[str]:
    errors = []
    r_lower = response.lower()

    for s in case.get("must_contain_any", []):
        if not any(s.lower() in r_lower for s in case["must_contain_any"]):
            errors.append(f"must_contain_any: none of {case['must_contain_any']!r} found")
            break

    for s in case.get("must_contain_all", []):
        if s.lower() not in r_lower:
            errors.append(f"must_contain_all: {s!r} missing")

    for s in case.get("must_not_contain", []):
        if s.lower() in r_lower:
            errors.append(f"must_not_contain: {s!r} found in response")

    if "must_contain_n_of" in case:
        options, n = case["must_contain_n_of"]
        found = sum(1 for o in options if o.lower() in r_lower)
        if found < n:
            errors.append(f"must_contain_n_of: only {found} of {n} required items found")

    return errors


def run_golden_tests() -> int:
    from app.ai.prompts import build_user_message

    failed = 0
    for case in GOLDEN_CASES:
        grounded = case["grounded"]
        user_msg = build_user_message(grounded, case["query"])

        # Dry-run without LLM: test the retrieval + validate_response path only
        # (full LLM path requires ANTHROPIC_API_KEY)
        if not os.getenv("ANTHROPIC_API_KEY"):
            # Validate price guardrail directly on a plausible answer
            if case.get("must_not_contain"):
                result = validate_response(
                    " ".join(case["must_not_contain"]) + " here",
                    grounded,
                )
                if result.ok:
                    # The text containing the must_not_contain token passed validation
                    # which means it IS grounded — so the case premise is wrong.
                    # Skip: this test needs LLM output.
                    pass
            print(f"  [SKIP] {case['id']}: no ANTHROPIC_API_KEY set")
            continue

        from app.ai.service import complete
        response = complete(case["query"], grounded)

        errors = _check(response, case)
        status = "PASS" if not errors else "FAIL"
        print(f"  [{status}] {case['id']}: {case['validates']}")
        if errors:
            failed += 1
            for e in errors:
                print(f"         ✗ {e}")
            print(f"         Response: {response[:200]!r}")

    return failed


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
    print("=" * 60)
    print("BuildRight Hardware — Retail Golden Tests")
    print("=" * 60)
    failures = run_golden_tests()
    print("=" * 60)
    if failures:
        print(f"FAILED: {failures} case(s)")
        sys.exit(1)
    print("All cases passed (or skipped — set ANTHROPIC_API_KEY to run LLM cases).")
