"""Anthropic-shaped ⇄ OpenAI translation: tools, multi-round tool threading, images."""

from __future__ import annotations

from app.ai.providers.base import Block
from app.ai.providers.openai_compat import (
    from_openai_message,
    to_openai_messages,
    to_openai_tools,
)


def test_tools_translate_input_schema_to_parameters():
    tools = [{
        "name": "search_products",
        "description": "Search the catalog",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}},
    }]
    out = to_openai_tools(tools)
    assert out[0]["type"] == "function"
    assert out[0]["function"]["name"] == "search_products"
    assert out[0]["function"]["parameters"]["properties"]["query"]["type"] == "string"


def test_full_tool_round_threading():
    """A user turn, an assistant tool_use round, and its tool_result — the exact message
    shapes stream_chat appends — must round-trip into valid OpenAI messages."""
    messages = [
        {"role": "user", "content": "find a drill"},
        {"role": "assistant", "content": [
            Block(type="text", text="Let me check."),
            Block(type="tool_use", id="t1", name="search_products", input={"query": "drill"}),
        ]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "t1", "content": '{"results": []}'},
        ]},
    ]
    out = to_openai_messages("SYS", messages)
    assert out[0] == {"role": "system", "content": "SYS"}
    assert out[1] == {"role": "user", "content": "find a drill"}
    asst = out[2]
    assert asst["role"] == "assistant" and asst["content"] == "Let me check."
    assert asst["tool_calls"][0]["id"] == "t1"
    assert asst["tool_calls"][0]["function"]["name"] == "search_products"
    assert '"query": "drill"' in asst["tool_calls"][0]["function"]["arguments"]
    tool = out[3]
    assert tool == {"role": "tool", "tool_call_id": "t1", "content": '{"results": []}'}


def test_image_block_becomes_data_uri():
    messages = [{"role": "user", "content": [
        {"type": "text", "text": "what is this?"},
        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "AAAA"}},
    ]}]
    out = to_openai_messages("", messages)
    parts = out[0]["content"]
    assert parts[0] == {"type": "text", "text": "what is this?"}
    assert parts[1]["image_url"]["url"] == "data:image/png;base64,AAAA"


def test_from_openai_message_tool_calls_and_stop_reason():
    class _Fn:
        name = "search_products"
        arguments = '{"query": "saw"}'

    class _TC:
        id = "call_1"
        function = _Fn()

    class _Msg:
        content = None
        tool_calls = [_TC()]

    class _Usage:
        prompt_tokens = 10
        completion_tokens = 4

    resp = from_openai_message(_Msg(), "tool_calls", _Usage(), "llama-3.3-70b")
    assert resp.stop_reason == "tool_use"
    b = resp.content[0]
    assert b.type == "tool_use" and b.name == "search_products" and b.input == {"query": "saw"}
    assert resp.usage.input_tokens == 10 and resp.usage.output_tokens == 4


def test_from_openai_message_plain_text():
    class _Msg:
        content = "The saw is in stock."
        tool_calls = None

    resp = from_openai_message(_Msg(), "stop", None, "m")
    assert resp.stop_reason == "end_turn"
    assert resp.content[0].type == "text" and "saw" in resp.content[0].text


def test_malformed_tool_arguments_degrade_to_empty_input():
    class _Fn:
        name = "search_products"
        arguments = "{not json"

    class _TC:
        id = "c1"
        function = _Fn()

    class _Msg:
        content = None
        tool_calls = [_TC()]

    resp = from_openai_message(_Msg(), "tool_calls", None, "m")
    assert resp.content[0].input == {}
