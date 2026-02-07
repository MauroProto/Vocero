import logging
from enum import StrEnum

from fastapi import APIRouter, Request, Response, HTTPException
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from app.config import settings
from app.services.contact import download_and_parse_vcard, extract_phone_from_text
from app.services.transcription import download_media, transcribe_audio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["whatsapp"])


class MessageType(StrEnum):
    TEXT = "text"
    VOICE_NOTE = "voice_note"
    CONTACT = "contact"


def _classify_message(num_media: int, media_type: str | None) -> MessageType:
    if num_media == 0:
        return MessageType.TEXT
    if media_type and media_type.startswith("audio/"):
        return MessageType.VOICE_NOTE
    if media_type and media_type.startswith("text/vcard"):
        return MessageType.CONTACT
    return MessageType.TEXT


def _validate_signature(request: Request, form_params: dict[str, str]) -> bool:
    """Validate Twilio request signature. Uses app_base_url to reconstruct the public URL."""
    if settings.debug:
        return True

    validator = RequestValidator(settings.twilio_auth_token)
    # Behind ngrok/proxy, request.url is localhost — use app_base_url instead
    public_url = settings.app_base_url.rstrip("/") + "/api/whatsapp"
    signature = request.headers.get("X-Twilio-Signature", "")
    return validator.validate(public_url, form_params, signature)


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    form = await request.form()
    form_params = {k: str(v) for k, v in form.items()}

    if not _validate_signature(request, form_params):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    from_number = form_params.get("From", "")
    body = form_params.get("Body", "")
    profile_name = form_params.get("ProfileName", "")
    num_media = int(form_params.get("NumMedia", "0"))
    media_url = form_params.get("MediaUrl0")
    media_type = form_params.get("MediaContentType0")

    msg_type = _classify_message(num_media, media_type)

    logger.info(
        "WhatsApp from %s (%s): type=%s body=%s",
        from_number, profile_name, msg_type, body[:100] if body else "<empty>",
    )

    twiml = MessagingResponse()

    if msg_type == MessageType.CONTACT and media_url:
        contact = await download_and_parse_vcard(media_url)
        if contact:
            twiml.message(
                f"Contact received:\n*Name:* {contact.name or 'Unknown'}\n*Phone:* {contact.phone}"
            )
        else:
            twiml.message("Could not parse the shared contact. Please try sending the phone number as text.")
    elif msg_type == MessageType.TEXT:
        phone = extract_phone_from_text(body)
        if phone:
            twiml.message(f"Phone number detected: {phone}")
        else:
            twiml.message(f"Echo: {body}")
    elif msg_type == MessageType.VOICE_NOTE and media_url:
        audio_bytes = await download_media(media_url)
        transcription = await transcribe_audio(audio_bytes)
        lang_label = "Spanish" if transcription.language.startswith("es") else (
            "English" if transcription.language.startswith("en") else transcription.language
        )
        twiml.message(
            f"Transcription ({lang_label}):\n_{transcription.text}_"
        )

    return Response(content=str(twiml), media_type="application/xml")
