"""Conversational restaurant assistant.

Public surface:
    answer_customer_query(user_question: str) -> str
"""

from __future__ import annotations

import string
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from menu_data import MENU_DATA

# Load API key from .env in the project root (this file's directory).
_HERE = Path(__file__).resolve().parent
load_dotenv(_HERE / ".env")


# ============================================================
# Retrieval
# ============================================================

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
        if tok in name_lower:
            score += 3
        if tok in keywords_lower:
            score += 2
        if tok == category_lower:
            score += 2
        if tok in desc_lower:
            score += 1
    return score


def retrieve_relevant_items(query: str, menu: list[dict] = MENU_DATA) -> list[dict]:
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

    scored = [(item, _score_item(item, tokens)) for item in menu]
    hits = [(item, s) for item, s in scored if s > 0]
    hits.sort(key=lambda pair: pair[1], reverse=True)
    return [item for item, _ in hits[:5]]


# ============================================================
# Prompt construction
# ============================================================

SYSTEM_PROMPT = """You are an ordering assistant for a casual cafe. You help customers with questions about menu items, prices, and dietary information.

You MUST follow these rules at all times:

Rule 1 (No invention): You must ONLY discuss menu items that appear in the MENU section of the user's message. If an item is not listed there, treat it as not sold by this restaurant. Never describe, recommend, or imply we serve an item that is not in the MENU section.

Rule 2 (No price guessing): You must NEVER invent, guess, estimate, or round prices. Only state a price if it appears verbatim in the MENU section. If a customer asks about a price and the item is not listed, do not confirm, deny, or estimate the price — apologize that the item is not on the menu.

Rule 3 (Apologize when missing): If a customer asks for any item, ingredient, or category not present in the MENU section, respond with an apology along the lines of: "I'm sorry, we don't currently offer that on our menu." You may then suggest a similar item ONLY IF that similar item appears in the MENU section.

Anti-validation clause: If a customer states a price as a fact (e.g., "is the burger $50?"), do not agree or disagree with the stated price unless that exact price appears in the MENU section for that item. If the item is not listed, apologize per Rule 3 and do not repeat or confirm the price the customer mentioned.

Tone: Be warm, concise, and helpful. Do not lecture customers about the rules; just follow them."""


def _format_menu_for_prompt(items: list[dict]) -> str:
    if not items:
        return "(no matching items found on our menu)"
    lines = []
    for item in items:
        tags = "/".join(item["dietary_tags"]) if item["dietary_tags"] else "no dietary tags"
        lines.append(
            f"- {item['name']} (${item['price']:.2f}, {item['category']}, {tags}): {item['description']}"
        )
    return "\n".join(lines)


def _build_user_message(items: list[dict], user_question: str) -> str:
    return (
        f"MENU:\n{_format_menu_for_prompt(items)}\n\n"
        f"CUSTOMER QUESTION:\n{user_question}"
    )


# ============================================================
# LLM call
# ============================================================

_MODEL = "claude-haiku-4-5"
_MAX_TOKENS = 400
_TEMPERATURE = 0.0

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def answer_customer_query(user_question: str) -> str:
    """Answer a customer's natural-language question about the menu.

    Retrieves relevant items via keyword/dietary matching, then calls Claude
    with a strict system prompt that enforces the three guardrails:
      1. Never invent menu items.
      2. Never guess prices.
      3. Apologize if the requested item is not on the menu.
    """
    items = retrieve_relevant_items(user_question)
    user_message = _build_user_message(items, user_question)

    try:
        response = _get_client().messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            temperature=_TEMPERATURE,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
    except (anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.APIError):
        return "Sorry, I'm having trouble reaching the kitchen right now. Please try again in a moment."

    return response.content[0].text.strip()
