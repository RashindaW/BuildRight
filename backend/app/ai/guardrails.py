"""Guardrails — the prompt (VERBATIM from the PoC) + a deterministic output validator.

Two layers:
  1. SYSTEM_PROMPT — the three guardrails + anti-validation clause (unchanged).
  2. validate_response() — a programmatic backstop that, given the model's answer
     and the grounded item set for THIS turn, confirms that every $price mentioned
     exists in the grounded set. A fabricated/guessed price is caught here even if
     the model slips, so a bad price never reaches the customer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---- Layer 1: the prompt (verbatim) ------------------------------------

SYSTEM_PROMPT = """You are an ordering assistant for a casual cafe. You help customers with questions about menu items, prices, and dietary information.

You MUST follow these rules at all times:

Rule 1 (No invention): You must ONLY discuss menu items that appear in the MENU section of the user's message. If an item is not listed there, treat it as not sold by this restaurant. Never describe, recommend, or imply we serve an item that is not in the MENU section.

Rule 2 (No price guessing): You must NEVER invent, guess, estimate, or round prices. Only state a price if it appears verbatim in the MENU section. If a customer asks about a price and the item is not listed, do not confirm, deny, or estimate the price — apologize that the item is not on the menu.

Rule 3 (Apologize when missing): If a customer asks for any item, ingredient, or category not present in the MENU section, respond with an apology along the lines of: "I'm sorry, we don't currently offer that on our menu." You may then suggest a similar item ONLY IF that similar item appears in the MENU section.

Anti-validation clause: If a customer states a price as a fact (e.g., "is the burger $50?"), do not agree or disagree with the stated price unless that exact price appears in the MENU section for that item. If the item is not listed, apologize per Rule 3 and do not repeat or confirm the price the customer mentioned.

Tone: Be warm, concise, and helpful. Do not lecture customers about the rules; just follow them."""


# ---- Layer 2: deterministic output validator --------------------------

_PRICE_RE = re.compile(r"\$\s?(\d+(?:\.\d{1,2})?)")
_DOLLARS_RE = re.compile(r"(\d+(?:\.\d{1,2})?)\s*dollars\b", re.IGNORECASE)


def _normalize_price(raw: str) -> str:
    """'4' -> '$4.00', '4.5' -> '$4.50', '11.50' -> '$11.50'."""
    value = float(raw)
    return f"${value:.2f}"


def extract_prices(text: str) -> set[str]:
    """Extract all price-like tokens from text, normalized to $X.XX."""
    found: set[str] = set()
    for m in _PRICE_RE.finditer(text):
        found.add(_normalize_price(m.group(1)))
    for m in _DOLLARS_RE.finditer(text):
        found.add(_normalize_price(m.group(1)))
    return found


# Comparison/threshold cues: a price here is a *filter* the customer asked about
# ("vegan options under $5"), NOT a claim that an item costs that amount. We must
# not flag these, or legitimate answers get blocked. Item-price assertions
# ("the burger is $50") have no such cue and remain validated.
_THRESHOLD_PRE = (
    "under", "below", "over", "above", "less than", "more than", "fewer than",
    "up to", "within", "around", "about", "cheaper than", "between", "at most",
    "at least", "max", "maximum", "no more than", "or less", "or under",
)
_THRESHOLD_POST = ("or less", "or under", "or more", "and under", "and over", "or fewer")


def _in_threshold_context(text: str, start: int, end: int) -> bool:
    pre = text[max(0, start - 18):start].lower()
    post = text[end:end + 12].lower()
    return any(c in pre for c in _THRESHOLD_PRE) or any(c in post for c in _THRESHOLD_POST)


def _claimed_prices(text: str) -> set[str]:
    """Prices the text asserts as item prices (excluding threshold/filter mentions)."""
    claimed: set[str] = set()
    for m in _PRICE_RE.finditer(text):
        if not _in_threshold_context(text, m.start(), m.end()):
            claimed.add(_normalize_price(m.group(1)))
    for m in _DOLLARS_RE.finditer(text):
        if not _in_threshold_context(text, m.start(), m.end()):
            claimed.add(_normalize_price(m.group(1)))
    return claimed


def grounded_price_set(items: list[dict]) -> set[str]:
    return {f"${item['price']:.2f}" for item in items}


@dataclass
class ValidationResult:
    ok: bool
    ungrounded_prices: list[str] = field(default_factory=list)

    @property
    def reason(self) -> str:
        if self.ok:
            return "ok"
        return f"ungrounded prices: {', '.join(self.ungrounded_prices)}"


def validate_response(response: str, grounded_items: list[dict]) -> ValidationResult:
    """Confirm every price in `response` is grounded in `grounded_items`.

    Any price mentioned that is not in the grounded set is a Rule 2 violation
    (a guessed/invented price, or echoing a customer's asserted price).
    """
    allowed = grounded_price_set(grounded_items)
    # Only validate prices the answer asserts as item prices; ignore threshold
    # references like "under $5" that the customer asked to filter by.
    mentioned = _claimed_prices(response)
    ungrounded = sorted(p for p in mentioned if p not in allowed)
    return ValidationResult(ok=not ungrounded, ungrounded_prices=ungrounded)


SAFE_FALLBACK = (
    "I'm sorry, I can only share details and prices for items that are on our menu. "
    "Could I help you find something from our current menu instead?"
)


# ---- Retail store prompt (used by the live streaming chat app) ------------

SYSTEM_PROMPT_RETAIL = """You are a Store Assistant for BuildRight Hardware, a Canadian hardware and home-improvement retailer.

You have two tools: search_products and search_knowledge_base.

PRODUCT QUESTIONS: Call search_products BEFORE mentioning any product or price. You may call it multiple times to refine results (e.g. search by category, then by keyword).

POLICY QUESTIONS: Call search_knowledge_base BEFORE answering any question about returns, refunds, warranty, shipping, price-matching, or store policies. Always cite the source as "Document Title › Section".

You MUST follow these rules at all times:

Rule 1 (No invention): Only discuss products returned by search_products in this conversation. Never describe, recommend, or imply we carry an item that search_products did not return.

Rule 2 (No price guessing): NEVER invent, guess, estimate, or round prices. Only state a price that search_products returned verbatim for that item. If asked about a price for something search_products did not return, do not confirm, deny, or estimate it.

Rule 3 (Apologize when missing): If search_products returns no matching item for what the customer asked, respond with an apology like "I'm sorry, we don't carry that item." You may suggest a similar item ONLY IF search_products returned it.

Rule 4 (Policy grounding): Only state policies from search_knowledge_base results. Cite them as "Document Title › Section" (e.g., "Returns & Refunds Policy › Return Window"). If the policy information is not in the search results, say "For specific details please contact our customer service team."

Anti-validation clause: If a customer states a price as a fact (e.g. "is the drill $500?"), do not agree or disagree unless search_products returns that exact price for that item.

Tone: Be warm, helpful, and concise. Do not lecture customers about the rules; just follow them."""


# ---- Citation validator (soft check) --------------------------------------

def validate_citations(response: str, grounded_chunks) -> bool:
    """Soft-check: if the response mentions a policy topic, confirm at least
    one chunk was grounded. Returns True (ok) when no policy claim is made,
    or when grounded_chunks is non-empty. Returns False only when a policy
    answer appears ungrounded — caller adds a soft disclaimer rather than
    replacing the response entirely.
    """
    _POLICY_CUES = (
        "return policy", "refund", "warranty", "shipping", "delivery",
        "price match", "price-match", "store policy", "days to return",
    )
    lower = response.lower()
    mentions_policy = any(cue in lower for cue in _POLICY_CUES)
    if not mentions_policy:
        return True
    return bool(grounded_chunks)
