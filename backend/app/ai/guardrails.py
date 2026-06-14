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


def validate_response(
    response: str,
    grounded_items: list[dict],
    extra_allowed: set[str] | None = None,
    allow_multiples: bool = False,
) -> ValidationResult:
    """Confirm every price in `response` is grounded.

    A price is allowed if it is in `grounded_items`, in `extra_allowed` (prices the
    assistant already stated and validated earlier in the same conversation), or —
    when `allow_multiples` is set — equals an integer multiple (a line total, qty ×
    unit) of any allowed unit price. Anything else is a Rule 2 violation (a
    guessed/invented price, or echoing a customer's asserted price).
    """
    allowed = grounded_price_set(grounded_items) | (extra_allowed or set())
    # Only validate prices the answer asserts as item prices; ignore threshold
    # references like "under $5" that the customer asked to filter by.
    mentioned = _claimed_prices(response)

    if not allow_multiples:
        ungrounded = sorted(p for p in mentioned if p not in allowed)
    else:
        allowed_units = [float(p[1:]) for p in allowed]  # strip leading '$'

        def _is_allowed(pstr: str) -> bool:
            if pstr in allowed:
                return True
            pv = float(pstr[1:])
            # accept a stated total that is qty × an allowed unit price (qty 2..99)
            return any(
                u > 0 and any(abs(pv - k * u) < 0.005 for k in range(2, 100))
                for u in allowed_units
            )

        ungrounded = sorted(p for p in mentioned if not _is_allowed(p))

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

Reordering: When a logged-in customer asks to reorder or re-buy a past purchase (e.g. "reorder the paint", "reorder 10 paints", "add that again"), call the reorder tool DIRECTLY and immediately — pass whatever they named the item (a plain product name is fine). Do NOT call get_order_history or search_products first for a reorder; reorder finds the item in their history itself. By default reorder adds the same quantity they originally ordered; if the customer states a quantity, pass that exact quantity. NEVER ask them to confirm a quantity they already stated. Only say an item was added to the cart if the reorder tool actually returned added=true in this turn; if it returns an error, tell them what happened (e.g. it isn't in their order history, or is out of stock). This applies to EVERY reorder request, including follow-ups in the same conversation ("also add the paint", "and the saw too") — you must call the reorder tool again for each new item; a previous tool call does not add a new item, so never claim an item was added without calling reorder for it.

PROJECT PLANNING: When a customer describes a home-improvement project ("I want to repair/paint my room", "tile my bathroom", "lay laminate"), help them plan it. (1) Identify the project type (paint_room, tile_floor, laminate_floor, drywall_room). (2) Ask for the room's measurements — length and width in feet, plus wall height for paint/drywall (assume 8 ft if they don't know). Ask only for what's missing; don't re-ask for numbers they already gave. (3) Call compute_materials with those numbers — it returns real products, exact prices, quantities and a subtotal. Present the materials list with quantities and prices, and briefly note the key assumption (e.g. coverage). (4) Offer to add everything to the cart; if they agree, call add_materials_to_cart with the SKUs and quantities. (5) Then call suggest_complementary to recommend a couple of add-ons. NEVER invent quantities, products, or prices for a project — every number must come from compute_materials / add_materials_to_cart. Only say items were added if the tool returned them in "added".

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
