"""Voice → text for voice messages / voice ordering.

Speech-to-text needs an external provider. When STT_PROVIDER is configured the
audio is transcribed and the text can be fed straight into the normal chat /
reorder flow; when it isn't, the endpoint reports that clearly (no silent
failure, no fake transcript). Audio validation is pure and always available.
"""

from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger("app.ai.voice")

ALLOWED_AUDIO = {
    "audio/webm", "audio/ogg", "audio/mpeg", "audio/mp3", "audio/wav",
    "audio/x-wav", "audio/mp4", "audio/m4a", "audio/x-m4a",
}
MAX_AUDIO_BYTES = 20 * 1024 * 1024  # 20 MB


class VoiceError(Exception):
    """Invalid/oversized audio (HTTP 422)."""


class STTNotConfigured(Exception):
    """No speech-to-text provider configured (HTTP 503)."""


def is_configured() -> bool:
    return bool(settings.stt_provider) and settings.stt_api_key is not None


def validate_audio(data: bytes, media_type: str | None) -> str:
    mt = (media_type or "").split(";")[0].strip().lower()
    if mt not in ALLOWED_AUDIO:
        raise VoiceError("Unsupported audio type.")
    if not data:
        raise VoiceError("The audio is empty.")
    if len(data) > MAX_AUDIO_BYTES:
        raise VoiceError("Audio too large (max 20 MB).")
    return mt


# Provider → (OpenAI-compatible endpoint, default model). Groq is free-tier.
_PROVIDERS = {
    "openai": ("https://api.openai.com/v1/audio/transcriptions", "whisper-1"),
    "groq": ("https://api.groq.com/openai/v1/audio/transcriptions", "whisper-large-v3"),
}


def transcribe(data: bytes, media_type: str | None, *, filename: str = "audio.webm") -> str:
    """Transcribe audio to text. Raises STTNotConfigured when no provider is set."""
    validate_audio(data, media_type)
    if not is_configured():
        raise STTNotConfigured("No speech-to-text provider configured.")

    endpoint = _PROVIDERS.get(settings.stt_provider)
    if endpoint is None:
        raise STTNotConfigured(f"Unknown STT provider '{settings.stt_provider}'.")
    url, default_model = endpoint
    model = settings.stt_model or default_model
    return _transcribe_openai_compatible(url, model, data, filename)


def _transcribe_openai_compatible(  # pragma: no cover - needs a real key
    url: str, model: str, data: bytes, filename: str
) -> str:
    """OpenAI Whisper API + Groq share the same multipart contract."""
    import httpx

    key = settings.stt_api_key.get_secret_value()
    with httpx.Client(timeout=60.0) as client:
        r = client.post(
            url,
            headers={"Authorization": f"Bearer {key}"},
            data={"model": model},
            files={"file": (filename, data)},
        )
        r.raise_for_status()
        return (r.json().get("text") or "").strip()
