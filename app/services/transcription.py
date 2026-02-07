import logging
from dataclasses import dataclass
from io import BytesIO

import httpx
from elevenlabs.client import AsyncElevenLabs

from app.config import settings

logger = logging.getLogger(__name__)

_client: AsyncElevenLabs | None = None


def _get_client() -> AsyncElevenLabs:
    global _client
    if _client is None:
        _client = AsyncElevenLabs(api_key=settings.elevenlabs_api_key)
    return _client


@dataclass
class TranscriptionResult:
    text: str
    language: str
    language_probability: float


async def download_media(media_url: str) -> bytes:
    """Download media from Twilio using basic auth."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            media_url,
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
        )
        resp.raise_for_status()
        return resp.content


async def transcribe_audio(audio_bytes: bytes) -> TranscriptionResult:
    """Transcribe audio bytes using ElevenLabs Scribe V2. Auto-detects language."""
    client = _get_client()

    result = await client.speech_to_text.convert(
        file=BytesIO(audio_bytes),
        model_id="scribe_v2",
        tag_audio_events=False,
        diarize=False,
    )

    logger.info(
        "Transcription: lang=%s (%.2f) text=%s",
        result.language_code,
        result.language_probability,
        result.text[:100] if result.text else "<empty>",
    )

    return TranscriptionResult(
        text=result.text,
        language=result.language_code,
        language_probability=result.language_probability,
    )
