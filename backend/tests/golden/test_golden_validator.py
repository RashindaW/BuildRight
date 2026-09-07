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


# ---- Regression: thousands separators ---------------------------------------
#
# _PRICE_RE had no comma branch, so "$1,299.99" parsed as "$1" -> "$1.00" -> ungrounded,
# and a CORRECT answer was replaced with SAFE_FALLBACK. It fired on the 85 catalog items
# over $1,000 and on essentially every multi-item project subtotal.

BIG = [
    {"id": "mitre-saw", "name": "Sliding Mitre Saw", "category": "power-tools",
     "description": "", "price": 1299.99, "dietary_tags": [], "keywords": []},
    {"id": "drill", "name": "Cordless Drill", "category": "power-tools",
     "description": "", "price": 249.99, "dietary_tags": [], "keywords": []},
]


def test_comma_formatted_price_is_parsed_whole():
    assert extract_prices("It's $1,299.99") == {"$1299.99"}
    assert extract_prices("It's $1,299") == {"$1299.00"}
    assert extract_prices("1,299.99 dollars") == {"$1299.99"}
    assert extract_prices("$12,345,678.90") == {"$12345678.90"}


def test_comma_and_plain_forms_are_the_same_price():
    assert extract_prices("$1,299.99") == extract_prices("$1299.99")


def test_bare_thousands_number_is_not_a_price():
    assert extract_prices("We have 1,200 units in the warehouse.") == set()


def test_grounded_four_figure_price_passes_either_way():
    for ans in ("The Sliding Mitre Saw is $1,299.99.", "The Sliding Mitre Saw is $1299.99."):
        assert validate_response(ans, BIG).ok, ans


def test_fabricated_four_figure_price_still_blocked():
    r = validate_response("The Sliding Mitre Saw is $1,450.00.", BIG)
    assert not r.ok and "$1450.00" in r.ungrounded_prices


def test_comma_line_total_allowed_as_a_multiple():
    # 5 x $249.99 = $1,249.95 — a legitimate qty x unit line total.
    r = validate_response("Five drills come to $1,249.95.", BIG, allow_multiples=True)
    assert r.ok


# ---- Regression: hedge words are estimates, not thresholds -------------------
#
# "around"/"about" were treated as threshold cues, so "the drill is around $875" was
# never validated — a bypass that opened exactly when the model was least certain,
# and which Rule 2 forbids outright ("never invent, guess, estimate, or round").

def test_hedged_price_is_validated_not_excused():
    for ans in ("The drill is around $875.00.", "It costs about $999.99.",
                "Roughly $500.00 for that one."):
        r = validate_response(ans, BIG)
        assert not r.ok, f"hedged estimate slipped through: {ans}"


def test_hedged_but_grounded_price_still_passes():
    assert validate_response("It's around $249.99 for the drill.", BIG).ok


def test_real_thresholds_are_still_excused():
    for ans in ("Here are drills under $500.00.", "Anything $300.00 or less works.",
                "We have options up to $2,000.00."):
        assert validate_response(ans, BIG).ok, f"a genuine filter was flagged: {ans}"


def test_claimed_prices_separates_filters_from_assertions():
    from app.ai.guardrails import claimed_prices
    text = "Under $500.00 you have the Cordless Drill at $249.99."
    assert extract_prices(text) == {"$500.00", "$249.99"}   # every price mentioned
    assert claimed_prices(text) == {"$249.99"}              # only what is ASSERTED
