"""Retrieval pipeline — moved VERBATIM from the PoC assistant.py.

Pure and deterministic: no I/O, no API key needed. Operates on an injected
`menu: list[dict]` so it works identically against the in-memory MENU_DATA
(golden tests) and the DB-backed menu (production, via menu_adapter).

Item dict shape:
    {id, name, category, description, price, dietary_tags, keywords}
"""

from __future__ import annotations

import string

_STOPWORDS = {
    "a", "an", "the", "is", "are", "do", "you", "have", "has",
    "i", "me", "my", "please", "for", "with", "under", "over",
    "and", "or", "to", "of", "in", "on", "any", "anything",
    "what", "whats", "show",
}

# Exclusion filters (run first) — customer wants items WITHOUT the tag.
_NEGATIVE_DIETARY_PHRASES = [
    ("nut allergy", "contains-nuts"),
    ("nut-free", "contains-nuts"),
    ("nut free", "contains-nuts"),
    ("no nuts", "contains-nuts"),
    ("without nuts", "contains-nuts"),
]

# Inclusion filters — customer wants items WITH the tag.
_POSITIVE_DIETARY_PHRASES = [
    ("vegan", "vegan"),
    ("vegetarian", "vegetarian"),
    ("gluten free", "gluten-free"),
    ("gluten-free", "gluten-free"),
    ("celiac", "gluten-free"),
    ("dairy free", "dairy-free"),
    ("dairy-free", "dairy-free"),
    ("lactose", "dairy-free"),
    ("nuts", "contains-nuts"),
    ("nut", "contains-nuts"),
]

_GENERIC_BROWSE_PHRASES = [
    "what's on the menu",
    "whats on the menu",
    "what is on the menu",
    "see the menu",
    "the full menu",
    "your menu",
    "what do you have",
    "what do you sell",
    "what do you offer",
    "specials",
    "options",
]


def _tokenize(query: str) -> list[str]:
    lowered = query.lower()
    no_punct = lowered.translate(str.maketrans("", "", string.punctuation))
    return [t for t in no_punct.split() if t and t not in _STOPWORDS]


def _singularize(tok: str) -> str:
    """Naive depluralization so 'pizzas' matches 'pizza', 'drinks' -> 'drink'."""
    if len(tok) > 4 and tok.endswith("ies"):
        return tok[:-3] + "y"
    if len(tok) > 4 and tok.endswith("es") and tok[-3] in "sxz":
        return tok[:-2]
    if len(tok) > 3 and tok.endswith("s"):
        return tok[:-1]
    return tok


def _token_variants(tok: str) -> set[str]:
    return {tok, _singularize(tok)}


def _check_category(tokens: list[str], menu: list[dict]) -> list[dict] | None:
    """If the query names a category (e.g. 'pizzas', 'desserts'), return all of it."""
    categories = {item["category"] for item in menu}
    for tok in tokens:
        for v in _token_variants(tok):
            if v in categories:
                return [item for item in menu if item["category"] == v]
    return None


def _check_dietary_short_circuit(query_lower: str, menu: list[dict]) -> list[dict] | None:
    for phrase, tag in _NEGATIVE_DIETARY_PHRASES:
        if phrase in query_lower:
            return [item for item in menu if tag not in item["dietary_tags"]]
    for phrase, tag in _POSITIVE_DIETARY_PHRASES:
        if phrase in query_lower:
            return [item for item in menu if tag in item["dietary_tags"]]
    return None


def _is_generic_browse(query_lower: str) -> bool:
    return any(phrase in query_lower for phrase in _GENERIC_BROWSE_PHRASES)


def _score_item(item: dict, tokens: list[str]) -> int:
    score = 0
    name_lower = item["name"].lower()
    desc_lower = item["description"].lower()
    category_lower = item["category"].lower()
    keywords_lower = [k.lower() for k in item["keywords"]]
    for tok in tokens:
        # Match the token or its singular form (so plurals like "pizzas" hit).
        variants = _token_variants(tok)
        if any(v in name_lower for v in variants):
            score += 3
        if any(v in keywords_lower for v in variants):
            score += 2
        if any(v == category_lower for v in variants):
            score += 2
        if any(v in desc_lower for v in variants):
            score += 1
    return score


def retrieve_relevant_items(query: str, menu: list[dict]) -> list[dict]:
    """Return up to 5 menu items relevant to the query, or [] if none match.

    Order of checks:
      1. Dietary tag short-circuit (vegan, gluten-free, etc.) — returns filtered set.
      2. Generic-browse short-circuit ("what's on the menu") — returns full menu.
      3. Keyword scoring against name / keywords / category / description.
    """
    query_lower = query.lower()

    dietary_hits = _check_dietary_short_circuit(query_lower, menu)
    if dietary_hits is not None:
        return dietary_hits

    if _is_generic_browse(query_lower):
        return list(menu)

    tokens = _tokenize(query)
    if not tokens:
        return []

    # "what pizzas do you have?" / "show me desserts" -> return the whole category.
    category_hits = _check_category(tokens, menu)
    if category_hits:
        return category_hits

    scored = [(item, _score_item(item, tokens)) for item in menu]
    hits = [(item, s) for item, s in scored if s > 0]
    hits.sort(key=lambda pair: pair[1], reverse=True)
    return [item for item, _ in hits[:5]]
