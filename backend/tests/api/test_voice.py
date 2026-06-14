"""Voice transcription endpoint + validation (no STT provider configured in tests)."""

from __future__ import annotations

import pytest

from app.ai import voice

_AUDIO = ("clip.webm", b"fake-audio-bytes", "audio/webm")


def test_validate_audio_accepts_webm():
    assert voice.validate_audio(b"x", "audio/webm") == "audio/webm"


def test_validate_audio_rejects_non_audio():
    with pytest.raises(voice.VoiceError):
        voice.validate_audio(b"x", "image/png")


def test_validate_audio_rejects_oversize():
    with pytest.raises(voice.VoiceError):
        voice.validate_audio(b"x" * (voice.MAX_AUDIO_BYTES + 1), "audio/webm")


def test_not_configured_by_default():
    assert voice.is_configured() is False


def test_groq_provider_routes_to_groq_endpoint(monkeypatch):
    from pydantic import SecretStr
    from app.core.config import settings

    monkeypatch.setattr(settings, "stt_provider", "groq")
    monkeypatch.setattr(settings, "stt_api_key", SecretStr("gsk_test"))
    monkeypatch.setattr(settings, "stt_model", "")  # use the per-provider default

    captured = {}

    def fake_upload(url, model, data, filename):
        captured["url"] = url
        captured["model"] = model
        return "two cordless drills please"

    monkeypatch.setattr(voice, "_transcribe_openai_compatible", fake_upload)

    text = voice.transcribe(b"audio", "audio/webm")
    assert text == "two cordless drills please"
    assert captured["url"] == "https://api.groq.com/openai/v1/audio/transcriptions"
    assert captured["model"] == "whisper-large-v3"


def test_transcribe_endpoint_503_without_provider(client):
    r = client.post("/api/v1/media/transcribe", files={"file": _AUDIO})
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "stt_not_configured"


def test_transcribe_endpoint_rejects_non_audio(client):
    r = client.post("/api/v1/media/transcribe",
                    files={"file": ("x.png", b"img", "image/png")})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_audio"
