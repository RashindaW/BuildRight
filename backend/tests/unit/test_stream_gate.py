"""StreamingPriceGate: token-true price validation under adversarial chunking, plus the
full stream_chat loop with a scripted streaming fake client."""

from __future__ import annotations

import pytest

from app.ai import router, service
from app.ai.context import ToolContext
from app.ai.guardrails import SAFE_FALLBACK, StreamingPriceGate

ITEMS = [{"price": 12.99}, {"price": 4.00}]


def drain(gate: StreamingPriceGate, chunks: list[str]) -> str:
    out = ""
    for c in chunks:
        out += gate.feed(c)
        if gate.violation:
            return out
    out += gate.finish()
    return out


def test_grounded_price_split_across_chunks_passes():
    gate = StreamingPriceGate(ITEMS)
    text = "The drill costs $1" , "2.99 and it's in stock today, ready for pickup."
    out = drain(gate, list(text))
    assert gate.violation is None
    assert out == "The drill costs $12.99 and it's in stock today, ready for pickup."


def test_fabricated_price_never_emitted_even_partially():
    gate = StreamingPriceGate(ITEMS)
    # $999.99 is not grounded; stream it split awkwardly.
    chunks = ["Sure! The premium saw is $9", "9", "9.9", "9 which is a great deal, trust me on this one."]
    out = drain(gate, chunks)
    assert gate.violation == "$999.99"
    assert "$9" not in out, "no fragment of the fabricated price may render"


def test_threshold_context_is_not_a_claim():
    gate = StreamingPriceGate(ITEMS)
    out = drain(gate, ["Here are options under $5", " that work well for most small repair jobs."])
    assert gate.violation is None
    assert "under $5" in out


def test_line_total_multiple_allowed():
    gate = StreamingPriceGate(ITEMS)  # 3 × $4.00 = $12.00
    out = drain(gate, ["Three tubs come to $12.00 total for the whole project, a solid choice."])
    assert gate.violation is None
    assert "$12.00" in out


def test_dollars_word_form_validated():
    gate = StreamingPriceGate(ITEMS)
    chunks = ["That one is 55 dol", "lars even, and worth every penny for pros."]
    drain(gate, chunks)
    assert gate.violation == "$55.00"


def test_carried_price_allowed():
    gate = StreamingPriceGate([], extra_allowed={"$7.50"})
    out = drain(gate, ["As mentioned, it's $7.50 and still in stock at your local store."])
    assert gate.violation is None and "$7.50" in out


def test_tail_held_until_finish():
    gate = StreamingPriceGate(ITEMS)
    first = gate.feed("Short")
    assert first == ""  # entire text within HOLD window
    rest = gate.finish()
    assert first + rest == "Short"


# ---- full loop with a scripted STREAMING fake client -----------------------

class _Blk:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Usage:
    def __init__(self, i, o):
        self.input_tokens, self.output_tokens = i, o


class _Resp:
    def __init__(self, stop, content, i=1, o=1):
        self.stop_reason, self.content, self.usage = stop, content, _Usage(i, o)


class _Delta:
    type = "text_delta"

    def __init__(self, text):
        self.text = text


class _Ev:
    type = "content_block_delta"

    def __init__(self, text):
        self.delta = _Delta(text)


class _FakeStream:
    """Mimics anthropic's async message-stream context manager."""

    def __init__(self, deltas, final):
        self._deltas, self._final = deltas, final

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    def __aiter__(self):
        self._it = iter(self._deltas)
        return self

    async def __anext__(self):
        try:
            return _Ev(next(self._it))
        except StopIteration:
            raise StopAsyncIteration

    async def get_final_message(self):
        return self._final


def _client_with_script(script):
    class _Msgs:
        def stream(self, **kw):
            deltas, final = script.pop(0)
            return _FakeStream(deltas, final)

    class _Client:
        messages = _Msgs()

    return _Client()


@pytest.mark.asyncio
async def test_stream_chat_true_streaming_and_reset(monkeypatch):
    tool_resp = _Resp("tool_use", [_Blk(type="tool_use", name="search_products", id="t1", input={})])
    final_resp = _Resp("end_turn", [_Blk(type="text", text="ignored — deltas carry the text")])
    script = [
        # round 1: preamble longer than the gate's HOLD window (so part of it renders), then a tool call
        (["Let me look that up in our catalog right now — one moment while I check the stock."], tool_resp),
        (["The hammer is $4.00", " and ships today from our warehouse."], final_resp),  # round 2: final
    ]
    monkeypatch.setattr(service, "_get_async_client", lambda: _client_with_script(script))

    async def _fake_classify(client, q, has_image=False, model=None):
        return ("simple", "claude-haiku-4-5")

    monkeypatch.setattr(router, "classify_turn", _fake_classify)
    monkeypatch.setattr(
        service, "_build_executors",
        lambda: {"search_products": lambda inp, ctx: ('{"results": []}', [{"price": 4.00, "slug": "h"}])},
    )

    events = []
    async for ev in service.stream_chat([], ToolContext(menu=[], db=None), "hammer price?"):
        events.append(ev)

    kinds = [e["event"] for e in events]
    assert "delta_reset" in kinds, "interim pre-tool text must be reset"
    done = events[-1]
    assert done["event"] == "done"
    assert done["data"]["text"] == "The hammer is $4.00 and ships today from our warehouse."
    assert done["data"]["guardrail_violation"] is False
    # deltas arrived incrementally (more than one delta for the final answer)
    final_deltas = [e for e in events if e["event"] == "delta"]
    assert len(final_deltas) >= 2


@pytest.mark.asyncio
async def test_stream_chat_violation_replaces_with_fallback(monkeypatch):
    final_resp = _Resp("end_turn", [_Blk(type="text", text="x")])
    script = [(["This beauty is only $499.99", " — a total steal for the weekend."], final_resp)]
    monkeypatch.setattr(service, "_get_async_client", lambda: _client_with_script(script))

    async def _fake_classify(client, q, has_image=False, model=None):
        return ("simple", "claude-haiku-4-5")

    monkeypatch.setattr(router, "classify_turn", _fake_classify)
    monkeypatch.setattr(service, "_build_executors", lambda: {})

    events = []
    async for ev in service.stream_chat([], ToolContext(menu=[], db=None), "price?"):
        events.append(ev)

    emitted = "".join(e["data"]["text"] for e in events if e["event"] == "delta")
    assert "$499.99" not in emitted and "$4" not in emitted
    replaced = [e for e in events if e["event"] == "validated" and e["data"].get("replace")]
    assert replaced and replaced[0]["data"]["text"] == SAFE_FALLBACK
    done = events[-1]["data"]
    assert done["guardrail_violation"] is True
    assert done["text"] == SAFE_FALLBACK
