"""GV tier — keyless guardrail-validator tests.

Proves the deterministic output validator catches fabricated/guessed prices,
the anti-validation echo, and the price normalizer's edge cases — with NO API key.
This is the programmatic backstop behind the prompt's three guardrails.
"""

from __future__ import annotations

from app.ai.guardrails import extract_prices, validate_response

GROUNDED = [
    {"id": "classic-latte", "name": "Classic Latte", "category": "drink",
     "description": "", "price": 4.50, "dietary_tags": [], "keywords": []},
    {"id": "caesar-salad", "name": "Classic Caesar Salad", "category": "salad",
     "description": "", "price": 11.50, "dietary_tags": [], "keywords": []},
]


def test_normalizer_variants():
    assert extract_prices("It's $4.50") == {"$4.50"}
    assert extract_prices("It's $4.5") == {"$4.50"}
    assert extract_prices("4 dollars") == {"$4.00"}
    assert extract_prices("$11.50 and $4.50") == {"$11.50", "$4.50"}


def test_grounded_price_passes():
    r = validate_response("The Classic Latte is $4.50.", GROUNDED)
    assert r.ok


def test_fabricated_price_caught():
    r = validate_response("The burger is $50.00.", GROUNDED)
    assert not r.ok
    assert "$50.00" in r.ungrounded_prices


def test_anti_validation_echo_caught():
    # Customer asserts "is the burger $50?"; model must not echo $50.
    r = validate_response("Yes, the burger is $50!", GROUNDED)
    assert not r.ok


def test_apology_with_no_price_passes():
    r = validate_response("I'm sorry, we don't currently offer sushi on our menu.", GROUNDED)
    assert r.ok


def test_no_substring_false_positive():
    # "$11.50" must not be mistaken as containing an ungrounded "$1.50".
    r = validate_response("That's $11.50.", GROUNDED)
    assert r.ok


def test_empty_grounded_set_blocks_any_price():
    r = validate_response("It costs $3.00.", [])
    assert not r.ok


def test_threshold_price_not_flagged():
    # "under $5" is a filter the customer asked about, not an item-price claim.
    # The listed item prices are grounded; $5.00 is only the threshold -> must pass.
    ans = "Here are our vegan options under $5: Green Tea ($3.25) and Fresh Lemonade ($3.75)."
    r = validate_response(ans, GROUNDED + [
        {"id": "tea", "name": "Green Tea", "category": "drink", "description": "",
         "price": 3.25, "dietary_tags": [], "keywords": []},
        {"id": "lem", "name": "Fresh Lemonade", "category": "drink", "description": "",
         "price": 3.75, "dietary_tags": [], "keywords": []},
    ])
    assert r.ok, r.reason


def test_threshold_does_not_excuse_fabricated_item_price():
    # A real fabricated item price must still be caught even alongside a threshold.
    ans = "Options under $5: the Mega Burger is $50.00."
    r = validate_response(ans, GROUNDED)
    assert not r.ok and "$50.00" in r.ungrounded_prices
