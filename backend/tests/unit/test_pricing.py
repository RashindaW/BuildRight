"""Token→USD pricing tests (keyless)."""

from __future__ import annotations

from app.ai.pricing import cost_usd


def test_haiku_cost():
    # 1000 in * $1/Mtok + 500 out * $5/Mtok = 0.001 + 0.0025
    assert cost_usd("claude-haiku-4-5", 1000, 500) == 0.0035


def test_sonnet_cost():
    # 1000 in * $3 + 500 out * $15 = 0.003 + 0.0075
    assert cost_usd("claude-sonnet-4-6", 1000, 500) == 0.0105


def test_opus_more_expensive_than_sonnet():
    assert cost_usd("claude-opus-4-8", 1000, 1000) > cost_usd("claude-sonnet-4-6", 1000, 1000)


def test_unknown_model_is_zero():
    assert cost_usd("gpt-banana", 1000, 1000) == 0.0
    assert cost_usd(None, 10, 10) == 0.0


def test_zero_tokens_zero_cost():
    assert cost_usd("claude-haiku-4-5", 0, 0) == 0.0


def test_longest_prefix_wins():
    # 3-5-haiku has its own cheaper rate than the generic haiku family
    assert cost_usd("claude-3-5-haiku-20241022", 1_000_000, 0) == 0.80
    assert cost_usd("claude-haiku-4-5", 1_000_000, 0) == 1.00
