"""OpenAI-compatible provider — ONE adapter for vLLM, Groq, Gemini (OpenAI endpoint),
Together, OpenRouter, etc., differing only by base_url + api key.

Translates the app's canonical Anthropic-shaped request/response at this boundary:
  request : system str → leading system message; tools input_schema → function.parameters;
            assistant tool_use blocks → tool_calls; user tool_result blocks → role:"tool".
  response: message.content → text Block; tool_calls → tool_use Blocks (JSON args parsed);
            finish_reason "tool_calls" → stop_reason "tool_use", else "end_turn".
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from app.ai.providers.base import (
    Block,
    LLMResponse,
    ProviderBadRequestError,
    ProviderConnectionError,
    ProviderError,
    ProviderRateLimitError,
    ProviderServerError,
    Usage,
)

logger = logging.getLogger("app.ai.providers.openai")


def _get(obj: Any, key: str, default=None):
    """Attribute-or-dict access — history blocks may be SDK objects, dataclasses, or dicts."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def to_openai_tools(tools: list[dict]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
            },
        }
        for t in tools
    ]


def to_openai_messages(system: str, messages: list[dict]) -> list[dict]:
    out: list[dict] = []
    if system:
        out.append({"role": "system", "content": system})
    for m in messages:
        role, content = m.get("role"), m.get("content")
        if isinstance(content, str):
            out.append({"role": role, "content": content})
            continue
        # content is a list of Anthropic-shaped blocks
        if role == "assistant":
            text_parts, tool_calls = [], []
            for b in content:
                btype = _get(b, "type")
                if btype == "text":
                    text_parts.append(_get(b, "text", ""))
                elif btype == "tool_use":
                    tool_calls.append({
                        "id": _get(b, "id", ""),
                        "type": "function",
                        "function": {
                            "name": _get(b, "name", ""),
                            "arguments": json.dumps(_get(b, "input", {}) or {}),
                        },
                    })
            msg: dict = {"role": "assistant", "content": "".join(text_parts) or None}
            if tool_calls:
                msg["tool_calls"] = tool_calls
            out.append(msg)
        else:  # user turn — may carry tool_result blocks or image blocks
            parts, tool_msgs = [], []
            for b in content:
                btype = _get(b, "type")
                if btype == "tool_result":
                    tool_msgs.append({
                        "role": "tool",
                        "tool_call_id": _get(b, "tool_use_id", ""),
                        "content": _get(b, "content", ""),
                    })
                elif btype == "image":
                    src = _get(b, "source", {}) or {}
                    parts.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{_get(src, 'media_type', 'image/jpeg')};base64,{_get(src, 'data', '')}"},
                    })
                elif btype == "text":
                    parts.append({"type": "text", "text": _get(b, "text", "")})
            # OpenAI wants tool results as standalone role:"tool" messages
            out.extend(tool_msgs)
            if parts:
                out.append({"role": "user", "content": parts})
    return out


def from_openai_message(msg: Any, finish_reason: str, usage: Any, model: str) -> LLMResponse:
    blocks: list[Block] = []
    content = _get(msg, "content")
    if content:
        blocks.append(Block(type="text", text=content))
    for tc in _get(msg, "tool_calls") or []:
        fn = _get(tc, "function")
        try:
            args = json.loads(_get(fn, "arguments") or "{}")
        except json.JSONDecodeError:
            logger.warning('"openai_tool_args_unparseable: %s"', _get(fn, "name"))
            args = {}
        blocks.append(Block(type="tool_use", id=_get(tc, "id", ""), name=_get(fn, "name", ""), input=args))
    stop = "tool_use" if finish_reason == "tool_calls" else "end_turn"
    return LLMResponse(
        content=blocks,
        stop_reason=stop,
        usage=Usage(_get(usage, "prompt_tokens", 0) or 0, _get(usage, "completion_tokens", 0) or 0),
        model=model,
    )


def _map_openai_error(e: Exception, provider: str, model: str) -> ProviderError | None:
    try:
        import openai
    except ImportError:
        return None
    if isinstance(e, openai.RateLimitError):
        return ProviderRateLimitError(str(e), provider=provider, model=model)
    if isinstance(e, openai.APIConnectionError):
        return ProviderConnectionError(str(e), provider=provider, model=model)
    if isinstance(e, openai.BadRequestError):
        return ProviderBadRequestError(str(e), provider=provider, model=model)
    if isinstance(e, openai.APIError):
        return ProviderServerError(str(e), provider=provider, model=model)
    return None


class OpenAICompatProvider:
    """Chat-completions provider over any OpenAI-compatible endpoint."""

    def __init__(self, *, name: str, model: str, base_url: str | None, api_key: str,
                 streaming: bool = True):
        self.name = name
        self._model = model
        self._base_url = base_url
        self._api_key = api_key
        self._streaming = streaming
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai  # lazy: only needed when an openai_compat model is enabled
            self._client = openai.AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
        return self._client

    def _request_kwargs(self, kwargs: dict) -> dict:
        req = {
            "model": self._model,  # provider-native name, not the registry id
            "messages": to_openai_messages(kwargs.get("system", ""), kwargs.get("messages", [])),
            "max_tokens": kwargs.get("max_tokens", 512),
            "temperature": kwargs.get("temperature", 0.0),
        }
        tools = kwargs.get("tools")
        if tools:
            req["tools"] = to_openai_tools(tools)
        return req

    async def complete(self, **kwargs) -> LLMResponse:
        try:
            r = await self._get_client().chat.completions.create(**self._request_kwargs(kwargs))
        except Exception as e:  # noqa: BLE001
            mapped = _map_openai_error(e, self.name, self._model)
            if mapped is not None:
                raise mapped from e
            raise
        choice = r.choices[0]
        return from_openai_message(choice.message, choice.finish_reason, r.usage, self._model)

    async def stream_events(self, **kwargs) -> AsyncIterator[tuple[str, Any]]:
        if not self._streaming:
            resp = await self.complete(**kwargs)
            text = "".join(b.text for b in resp.content if b.type == "text").strip()
            if text:
                yield ("delta", text)
            yield ("final", resp)
            return
        req = self._request_kwargs(kwargs)
        req["stream"] = True
        req["stream_options"] = {"include_usage": True}
        text_acc = ""
        tool_acc: dict[int, dict] = {}  # index -> {id, name, arguments}
        finish = None
        usage = None
        try:
            stream = await self._get_client().chat.completions.create(**req)
            async for chunk in stream:
                if getattr(chunk, "usage", None):
                    usage = chunk.usage
                if not chunk.choices:
                    continue
                ch = chunk.choices[0]
                delta = ch.delta
                if getattr(delta, "content", None):
                    text_acc += delta.content
                    yield ("delta", delta.content)
                for tc in getattr(delta, "tool_calls", None) or []:
                    slot = tool_acc.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                    if getattr(tc, "id", None):
                        slot["id"] = tc.id
                    fn = getattr(tc, "function", None)
                    if fn is not None:
                        if getattr(fn, "name", None):
                            slot["name"] += fn.name
                        if getattr(fn, "arguments", None):
                            slot["arguments"] += fn.arguments
                if ch.finish_reason:
                    finish = ch.finish_reason
        except Exception as e:  # noqa: BLE001
            mapped = _map_openai_error(e, self.name, self._model)
            if mapped is not None:
                raise mapped from e
            raise

        blocks: list[Block] = []
        if text_acc:
            blocks.append(Block(type="text", text=text_acc))
        for idx in sorted(tool_acc):
            slot = tool_acc[idx]
            try:
                args = json.loads(slot["arguments"] or "{}")
            except json.JSONDecodeError:
                logger.warning('"openai_stream_tool_args_unparseable: %s"', slot["name"])
                args = {}
            blocks.append(Block(type="tool_use", id=slot["id"], name=slot["name"], input=args))
        stop = "tool_use" if (finish == "tool_calls" or tool_acc) else "end_turn"
        yield ("final", LLMResponse(
            content=blocks,
            stop_reason=stop,
            usage=Usage(_get(usage, "prompt_tokens", 0) or 0, _get(usage, "completion_tokens", 0) or 0),
            model=self._model,
        ))
