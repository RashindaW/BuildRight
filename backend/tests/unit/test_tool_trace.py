"""stream_chat emits the per-turn observability trace (tools_used / tool_rounds / model / route)."""

from __future__ import annotations

import pytest

from app.ai import router, service
from app.ai.context import ToolContext


class _Blk:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Usage:
    def __init__(self, i, o):
        self.input_tokens, self.output_tokens = i, o


class _Resp:
    def __init__(self, stop, content, i, o):
        self.stop_reason, self.content, self.usage = stop, content, _Usage(i, o)


@pytest.mark.asyncio
async def test_done_event_carries_tool_trace(monkeypatch):
    # Round 1: a tool_use(search_products); round 2: final text.
    responses = [
        _Resp("tool_use", [_Blk(type="tool_use", name="search_products", id="t1", input={})], 5, 3),
        _Resp("end_turn", [_Blk(type="text", text="Here are some drills.")], 4, 6),
    ]

    class _Msgs:
        async def create(self, **kw):
            return responses.pop(0)

    class _Client:
        messages = _Msgs()

    async def _fake_classify(client, q, has_image=False, model=None):
        return ("simple", "claude-haiku-4-5")

    monkeypatch.setattr(service, "_get_async_client", lambda: _Client())
    monkeypatch.setattr(router, "classify_turn", _fake_classify)
    monkeypatch.setattr(
        service, "_build_executors",
        lambda: {"search_products": lambda inp, ctx: ('{"results": []}', [])},
    )

    ctx = ToolContext(menu=[], db=None)
    done = None
    async for ev in service.stream_chat([], ctx, "find a cordless drill"):
        if ev["event"] == "done":
            done = ev["data"]

    assert done is not None
    assert done["tools_used"] == ["search_products"]
    assert done["tool_rounds"] == 1
    assert done["model"] == "claude-haiku-4-5"
    assert done["route"] == "simple"
    assert done["input_tokens"] == 9   # 5 + 4 accumulated across rounds
    assert done["output_tokens"] == 9  # 3 + 6
