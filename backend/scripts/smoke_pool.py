"""Go/no-go gate for a pool model: can it drive the REAL agent loop end-to-end?

    LOCAL_POOL_BASE_URL=http://<ip>:8000/v1 LOCAL_POOL_API_KEY=... \
        python -m scripts.smoke_pool amd-qwen-72b

Runs the actual stream_chat (real tools, real guardrails, seeded DB) against the given
registry model id and asserts: (1) a tool call round-trips (hermes parser fidelity —
the #1 risk on vLLM), (2) a grounded final answer arrives, (3) the guardrail passed.
Only after this passes should the model be treated as tools-capable in production.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def main(model_id: str) -> int:
    from app.ai import service
    from app.ai.context import ToolContext
    from app.ai.menu_adapter import get_menu_for_assistant
    from app.ai.registry import registry
    from app.core.db import SessionLocal

    registry.reload()
    entry = registry.get(model_id)
    if entry is None:
        print(f"FAIL: '{model_id}' not in models.yaml")
        return 1
    if not entry.configured:
        print(f"FAIL: '{model_id}' not configured (base_url={entry.effective_base_url!r}, "
              f"key_env={entry.api_key_env} set={bool(entry.api_key)})")
        return 1
    print(f"model: {model_id} -> {entry.model} @ {entry.effective_base_url}")

    db = SessionLocal()
    try:
        ctx = ToolContext(menu=get_menu_for_assistant(db), db=db)
        provider = registry.acquire(model_id)

        # Drive the real loop with the routed model forced to the pool model.
        events = []
        async for ev in service.stream_chat(
            [], ctx, "Do you have cordless drills, and how much is the cheapest one?",
            _forced_model=model_id,
        ):
            events.append(ev)
            if ev["event"] == "trace":
                print("  trace:", ev["data"])
    finally:
        db.close()

    done = next((e["data"] for e in reversed(events) if e["event"] == "done"), None)
    if done is None:
        print("FAIL: no done event (stream error?)")
        return 1

    tools_used = done.get("tools_used") or []
    ok_tool = any(t in ("search_products", "search_menu") for t in tools_used)
    ok_text = bool(done.get("text")) and done["text"] != ""
    ok_guard = not done.get("guardrail_violation", True)
    grounded = len(done.get("grounded_item_ids") or [])

    print(f"\ntools_used={tools_used} grounded_items={grounded} "
          f"guardrail_ok={ok_guard} tokens={done.get('input_tokens')}/{done.get('output_tokens')}")
    print("answer:", (done.get("text") or "")[:220])

    if ok_tool and ok_text and ok_guard:
        print(f"\nPASS — {model_id} drives the tool loop correctly; safe to mark tools-capable.")
        return 0
    print(f"\nFAIL — tool_call={ok_tool} text={ok_text} guardrail={ok_guard}")
    return 1


if __name__ == "__main__":
    mid = sys.argv[1] if len(sys.argv) > 1 else "amd-qwen-72b"
    raise SystemExit(asyncio.run(main(mid)))
