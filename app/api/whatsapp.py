import logging
from datetime import datetime, timezone
from enum import StrEnum

from fastapi import APIRouter, Request, Response, HTTPException
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from app.config import settings
from app.schemas.intent import IntentResult, IntentType
from app.services.contact import download_and_parse_vcard
from app.services.intent import extract_intent
from app.services.state import (
    ConversationState,
    ConversationStatus,
    build_context,
    get_state,
    merge_entities,
    reset_state,
)
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


def _handle_intent(state: ConversationState, result: IntentResult) -> None:
    """Update conversation state based on parsed intent. Mutates state in place."""
    state.pending_entities = merge_entities(state.pending_entities, result.entities)
    state.language = result.language
    state.updated_at = datetime.now(timezone.utc)

    if result.intent == IntentType.REQUEST_APPOINTMENT:
        state.pending_intent = IntentType.REQUEST_APPOINTMENT
        state.status = ConversationStatus.AWAITING_PROVIDER

    elif result.intent == IntentType.CALL_NUMBER:
        state.pending_intent = IntentType.CALL_NUMBER
        if result.entities.phone_number:
            state.provider_phone = result.entities.phone_number
        if result.entities.provider_name:
            state.provider_name = result.entities.provider_name
        state.status = ConversationStatus.CALLING

    elif result.intent == IntentType.CONFIRM:
        if (
            state.status == ConversationStatus.AWAITING_PROVIDER
            and state.pending_entities
            and state.pending_entities.phone_number
        ):
            state.status = ConversationStatus.CALLING

    elif result.intent == IntentType.CANCEL:
        state.status = ConversationStatus.IDLE
        state.pending_intent = None
        state.pending_entities = None
        state.provider_phone = None
        state.provider_name = None


def _process_intent(
    state: ConversationState,
    result: IntentResult,
    twiml: MessagingResponse,
    from_number: str,
) -> None:
    """Handle intent result: update state, set bot message, write TwiML."""
    old_status = state.status
    _handle_intent(state, result)

    twiml.message(result.response_message)
    state.last_bot_message = result.response_message

    if state.status != old_status:
        logger.info(
            "State transition for %s: %s -> %s",
            from_number, old_status, state.status,
        )


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

    # Get or create conversation state
    state = get_state(from_number)

    # Auto-reset completed conversations
    if state.status == ConversationStatus.COMPLETED:
        reset_state(from_number)
        state = get_state(from_number)

    logger.info(
        "WhatsApp from %s (%s): type=%s state=%s body=%s",
        from_number, profile_name, msg_type, state.status,
        body[:100] if body else "<empty>",
    )

    twiml = MessagingResponse()
    context = build_context(state)

    if msg_type == MessageType.CONTACT and media_url:
        try:
            contact = await download_and_parse_vcard(media_url)
        except Exception:
            logger.exception("Failed to process shared contact")
            contact = None

        if contact:
            state.provider_phone = contact.phone
            state.provider_name = contact.name
            state.updated_at = datetime.now(timezone.utc)

            if state.status == ConversationStatus.AWAITING_PROVIDER:
                old_status = state.status
                state.status = ConversationStatus.CALLING
                service = (
                    state.pending_entities.service_type
                    if state.pending_entities and state.pending_entities.service_type
                    else "appointment"
                )
                msg = (
                    f"Got it! I'll call *{contact.name or 'the provider'}* "
                    f"at {contact.phone} for your {service}. Stand by..."
                )
                twiml.message(msg)
                state.last_bot_message = msg
                logger.info(
                    "State transition for %s: %s -> %s",
                    from_number, old_status, state.status,
                )
            else:
                msg = (
                    f"Contact saved: *{contact.name or 'Unknown'}* — {contact.phone}\n"
                    f"What would you like me to do? Send me what you need and I'll call them."
                )
                twiml.message(msg)
                state.last_bot_message = msg
        else:
            twiml.message("Could not parse the shared contact. Please try sending the phone number as text.")

    elif msg_type == MessageType.TEXT:
        try:
            result = await extract_intent(body, context=context)
            _process_intent(state, result, twiml, from_number)
        except Exception:
            logger.exception("Intent parsing failed")
            twiml.message(f"Echo: {body}")

    elif msg_type == MessageType.VOICE_NOTE and media_url:
        try:
            audio_bytes = await download_media(media_url)
            transcription = await transcribe_audio(audio_bytes)
            result = await extract_intent(transcription.text, context=context)
            _process_intent(state, result, twiml, from_number)
        except Exception:
            logger.exception("Failed to process voice note")
            twiml.message("Sorry, I couldn't process your voice note. Please try again or send a text message.")

    return Response(content=str(twiml), media_type="application/xml")
