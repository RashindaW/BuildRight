"""Back-compat surface for the original PoC function + golden tests.

`answer_customer_query(user_question) -> str` behaves exactly like the PoC:
retrieve from the in-memory MENU_DATA, build the strict prompt, call Claude,
and now ALSO run the deterministic validator as an extra safety net.
"""

from __future__ import annotations

import sys
from pathlib import Path

from app.ai.retrieval import retrieve_relevant_items
from app.ai.service import complete

# Import the root-level menu_data.py (the v1 source of truth).
_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from menu_data import MENU_DATA  # noqa: E402


def answer_customer_query(user_question: str) -> str:
    items = retrieve_relevant_items(user_question, MENU_DATA)
    # Dietary/browse queries can return many items; give the model room to list
    # them all so the complete set (e.g. every vegan item) is never truncated.
    budget = 700 if len(items) > 5 else None
    return complete(user_question, items, max_tokens=budget)
