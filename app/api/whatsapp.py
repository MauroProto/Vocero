import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Response

from app.config import settings
from app.schemas.intent import IntentResult, IntentType, Language
from app.services.elevenlabs_call import fetch_conversation_details, make_outbound_call
from app.services.intent import extract_intent
from app.services.messages import (
    format_call_failed,
    format_calling_message,
    format_multi_call_start,
    format_search_results,
    format_transcript,
)
from app.services.places import search_places
from app.services.state import (
    ConversationState,
    ConversationStatus,
    MultiCallCampaign,
    MultiCallProvider,
    add_message,
    build_context,
    get_state,
    merge_entities,
    reset_state,
)
from app.services.transcription import transcribe_audio
from app.services.twilio import download_whatsapp_media, send_whatsapp_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["whatsapp"])

# Per-user lock to prevent concurrent message processing (avoids duplicate calls)
_user_locks: dict[str, asyncio.Lock] = {}

# Dedup: track recently processed message IDs (Meta can send duplicates)
_seen_message_ids: set[str] = set()


@dataclass
class ParsedContact:
    name: str | None
    phone: str | None


def _prepare_for_new_call(state: ConversationState) -> None:
    """Reset call-related state so a new call can be triggered."""
    state.active_call_ids.clear()
    state.call_results.clear()
    state.status = ConversationStatus.CALLING


def _handle_intent(state: ConversationState, result: IntentResult) -> None:
    """Update conversation state based on parsed intent. Mutates state in place."""
    state.pending_entities = merge_entities(state.pending_entities, result.entities)
    state.language = result.language
    state.updated_at = datetime.now(timezone.utc)

    if result.intent == IntentType.CALL_NUMBER:
        state.pending_intent = IntentType.CALL_NUMBER
        if result.entities.phone_number:
            state.provider_phone = result.entities.phone_number
        if result.entities.provider_name:
            state.provider_name = result.entities.provider_name
        # Only call immediately if we know what the user needs
        if result.entities.service_type:
            _prepare_for_new_call(state)
        else:
            state.status = ConversationStatus.AWAITING_PROVIDER

    elif result.intent == IntentType.REQUEST_APPOINTMENT:
        state.pending_intent = IntentType.REQUEST_APPOINTMENT
        # If we already have a phone from context, go straight to calling
        if state.provider_phone:
            _prepare_for_new_call(state)
        else:
            state.status = ConversationStatus.AWAITING_PROVIDER

    elif result.intent == IntentType.CONFIRM:
        if state.provider_phone:
            _prepare_for_new_call(state)

    elif result.intent == IntentType.CANCEL:
        state.status = ConversationStatus.IDLE
        state.pending_intent = None
        state.pending_entities = None
        state.provider_phone = None
        state.provider_name = None
        state.search_results = None
        state.active_call_ids.clear()

    elif result.intent == IntentType.SEARCH_PROVIDERS:
        state.pending_intent = IntentType.SEARCH_PROVIDERS
        state.status = ConversationStatus.AWAITING_PROVIDER


async def _send_and_track(state: ConversationState, from_number: str, msg: str) -> None:
    """Send a WhatsApp message and record it in state."""
    await send_whatsapp_message(from_number, msg)
    state.last_bot_message = msg
    add_message(state, "bot", msg)


async def _process_intent(
    state: ConversationState,
    result: IntentResult,
    from_number: str,
) -> None:
    """Handle intent result: update state, send response via Meta API."""
    old_status = state.status
    _handle_intent(state, result)

    # Don't send the LLM response if we're about to call — _trigger_call sends its own message
    if state.status == ConversationStatus.CALLING and state.provider_phone:
        state.last_bot_message = result.response_message
    else:
        await _send_and_track(state, from_number, result.response_message)

    if state.status != old_status:
        logger.info(
            "State transition for %s: %s -> %s",
            from_number, old_status, state.status,
        )


async def _trigger_call(from_number: str, state: ConversationState) -> None:
    """Place outbound call. Updates state with call IDs."""
    # Guard: only call if still in CALLING state with no active calls
    if state.status != ConversationStatus.CALLING or state.active_call_ids:
        return
    # Immediately mark as having a pending call to prevent re-entry
    state.active_call_ids.append("pending")

    lang = state.language.value
    entities = state.pending_entities

    dynamic_vars: dict[str, str] = {"language": lang}
    if state.user_name:
        dynamic_vars["user_name"] = state.user_name
    if state.provider_name:
        dynamic_vars["provider_name"] = state.provider_name
    if entities:
        if entities.service_type:
            dynamic_vars["service_type"] = entities.service_type
        if entities.date_preference:
            dynamic_vars["preferred_date"] = entities.date_preference
        if entities.time_preference:
            dynamic_vars["preferred_time"] = entities.time_preference
        if entities.special_requests:
            dynamic_vars["special_requests"] = entities.special_requests

    msg = format_calling_message(state.provider_name, state.provider_phone or "", language=lang)
    await send_whatsapp_message(from_number, msg)

    try:
        conversation_id, call_sid = await make_outbound_call(
            to_number=state.provider_phone or "",
            dynamic_variables=dynamic_vars,
            language=lang,
        )
        # Replace "pending" with actual IDs
        state.active_call_ids = [x for x in state.active_call_ids if x != "pending"]
        if conversation_id:
            state.active_call_ids.append(conversation_id)
        if call_sid:
            state.active_call_ids.append(call_sid)
        if not conversation_id and not call_sid:
            state.active_call_ids.clear()
            fail_msg = format_call_failed(state.provider_name, language=lang)
            await send_whatsapp_message(from_number, fail_msg)
            state.status = ConversationStatus.IDLE
    except Exception:
        logger.exception("Failed to place outbound call to %s", state.provider_phone)
        state.active_call_ids = [x for x in state.active_call_ids if x != "pending"]
        fail_msg = format_call_failed(state.provider_name, language=lang)
        await send_whatsapp_message(from_number, fail_msg)
        state.status = ConversationStatus.IDLE


async def _trigger_multi_call(from_number: str, state: ConversationState) -> None:
    """Place parallel outbound calls to multiple providers from search results."""
    if not state.search_results:
        return

    # Filter to providers with phone numbers, take first 3
    candidates = [r for r in state.search_results if r.phone][:3]
    if not candidates:
        lang = state.language.value
        msg = "Ninguno tiene telefono en Google." if lang == "es" else "None of them have a phone number on Google."
        await send_whatsapp_message(from_number, msg)
        return

    providers = [
        MultiCallProvider(
            name=r.name,
            phone=r.phone,
            rating=r.rating,
            total_ratings=r.total_ratings,
        )
        for r in candidates
    ]
    campaign = MultiCallCampaign(providers=providers, pending_count=len(providers))
    state.multi_call = campaign
    state.search_results = None
    state.status = ConversationStatus.CALLING

    lang = state.language.value
    msg = format_multi_call_start(len(providers), language=lang)
    await send_whatsapp_message(from_number, msg)

    entities = state.pending_entities
    dynamic_vars: dict[str, str] = {"language": lang}
    if state.user_name:
        dynamic_vars["user_name"] = state.user_name
    if entities:
        if entities.service_type:
            dynamic_vars["service_type"] = entities.service_type
        if entities.date_preference:
            dynamic_vars["preferred_date"] = entities.date_preference
        if entities.time_preference:
            dynamic_vars["preferred_time"] = entities.time_preference
        if entities.special_requests:
            dynamic_vars["special_requests"] = entities.special_requests

    for i, provider in enumerate(providers):
        if i > 0:
            await asyncio.sleep(1.5)  # Stagger for Twilio CPS

        call_vars = {**dynamic_vars, "provider_name": provider.name}
        try:
            conversation_id, call_sid = await make_outbound_call(
                to_number=provider.phone,
                dynamic_variables=call_vars,
                language=lang,
            )
            provider.conversation_id = conversation_id
            provider.call_sid = call_sid
            if conversation_id:
                state.active_call_ids.append(conversation_id)
            if call_sid:
                state.active_call_ids.append(call_sid)
            logger.info("Multi-call %d/%d: %s sid=%s conv=%s", i + 1, len(providers), provider.name, call_sid, conversation_id)
        except Exception:
            logger.exception("Failed to call %s", provider.name)
            campaign.pending_count -= 1
            campaign.results.append({
                "provider_name": provider.name,
                "phone": provider.phone,
                "rating": provider.rating,
                "total_ratings": provider.total_ratings,
                "summary": None,
                "outcome": "failed",
            })

    # If all calls failed immediately, send result now
    if campaign.pending_count <= 0:
        from app.services.ranking import rank_results
        from app.services.messages import format_ranked_results
        ranked = rank_results(campaign.results)
        msg = format_ranked_results(ranked, language=lang)
        await send_whatsapp_message(from_number, msg)
        state.status = ConversationStatus.COMPLETED
        state.multi_call = None


def _parse_meta_contact(message: dict) -> ParsedContact | None:
    """Extract contact info from a Meta WhatsApp contacts message."""
    contacts = message.get("contacts", [])
    if not contacts:
        return None
    contact = contacts[0]
    name = contact.get("name", {}).get("formatted_name")
    phones = contact.get("phones", [])
    phone = phones[0].get("phone") if phones else None
    if not phone:
        return None
    return ParsedContact(name=name, phone=phone)


async def _handle_message(from_number: str, profile_name: str, message: dict) -> None:
    """Process a single incoming WhatsApp message."""
    # Per-user lock prevents concurrent processing (avoids duplicate calls)
    if from_number not in _user_locks:
        _user_locks[from_number] = asyncio.Lock()
    async with _user_locks[from_number]:
        await _handle_message_inner(from_number, profile_name, message)


async def _handle_message_inner(from_number: str, profile_name: str, message: dict) -> None:
    """Process a single incoming WhatsApp message (serialized per user)."""
    msg_type = message.get("type", "")

    state = get_state(from_number)

    # Handle transcript request BEFORE reset (so last_conversation_id is still available)
    if msg_type == "text" and state.last_conversation_id:
        body_lower = message.get("text", {}).get("body", "").strip().lower()
        if body_lower in ("transcript", "transcripcion", "transcripción"):
            conv_data = await fetch_conversation_details(state.last_conversation_id)
            if conv_data:
                msg = format_transcript(state.provider_name or state.provider_phone, conv_data)
                await send_whatsapp_message(from_number, msg)
            else:
                no_msg = "No pude obtener el transcript." if state.language == Language.ES else "Couldn't retrieve the transcript."
                await send_whatsapp_message(from_number, no_msg)
            return

    # Auto-reset completed conversations so user can start fresh
    if state.status == ConversationStatus.COMPLETED:
        reset_state(from_number)
        state = get_state(from_number)

    # Store user's WhatsApp profile name
    if profile_name and not state.user_name:
        state.user_name = profile_name

    logger.info(
        "WhatsApp from %s (%s): type=%s state=%s",
        from_number, profile_name, msg_type, state.status,
    )

    context = build_context(state)

    # Handle search result selection
    if state.status == ConversationStatus.AWAITING_PROVIDER and state.search_results and msg_type == "text":
        body = message.get("text", {}).get("body", "").strip()
        body_lower = body.lower()

        # Check for "call all" trigger
        if body_lower in ("todos", "all", "llama a todos", "llamalos", "call all", "call them all"):
            asyncio.create_task(_trigger_multi_call(from_number, state))
            return

        if body.isdigit():
            idx = int(body) - 1
            if 0 <= idx < len(state.search_results):
                selected = state.search_results[idx]
                state.provider_name = selected.name
                state.provider_phone = selected.phone
                state.search_results = None
                state.updated_at = datetime.now(timezone.utc)
                if selected.phone:
                    _prepare_for_new_call(state)
                    lang = state.language.value
                    reason = (
                        state.pending_entities.service_type
                        if state.pending_entities and state.pending_entities.service_type
                        else None
                    )
                    if reason:
                        msg = f"Dale, ya llamo a *{selected.name}* por lo de {reason}!"
                    else:
                        msg = f"Dale, ya llamo a *{selected.name}*!"
                    await _send_and_track(state, from_number, msg)
                else:
                    await send_whatsapp_message(
                        from_number,
                        "Ese lugar no tiene telefono en Google. Pasame el numero como texto."
                        if state.language == Language.ES
                        else "That place doesn't have a phone number on Google. Send me the number as text."
                    )
                # Skip normal processing — we handled it
                if state.status == ConversationStatus.CALLING and state.provider_phone and not state.active_call_ids:
                    await _trigger_call(from_number, state)
                return
            else:
                n = len(state.search_results)
                lang = state.language.value
                oob_msg = f"Elegi un numero del 1 al {n}." if lang == "es" else f"Pick a number from 1 to {n}."
                await send_whatsapp_message(from_number, oob_msg)
                return

    if msg_type == "contacts":
        contact = _parse_meta_contact(message)
        if contact and contact.phone:
            state.provider_phone = contact.phone
            state.provider_name = contact.name
            state.updated_at = datetime.now(timezone.utc)

            # Check if we already know what the user needs
            has_context = state.pending_entities and state.pending_entities.service_type
            if has_context:
                _prepare_for_new_call(state)
                reason = state.pending_entities.service_type
                msg = f"Dale, ya llamo a *{contact.name or contact.phone}* por lo de {reason}!"
                await _send_and_track(state, from_number, msg)
            else:
                # Don't call blindly — ask what they need first
                state.status = ConversationStatus.AWAITING_PROVIDER
                state.pending_intent = IntentType.CALL_NUMBER
                lang = state.language.value
                name = contact.name or contact.phone
                if lang == "es":
                    msg = f"Tengo el numero de *{name}*. Que necesitas que le diga? (ej: reservar turno de corte para mañana a las 10)"
                else:
                    msg = f"Got *{name}*'s number. What do you need me to tell them? (e.g., book a haircut for tomorrow at 10)"
                await _send_and_track(state, from_number, msg)
        else:
            await send_whatsapp_message(
                from_number, "No pude leer el contacto. Mandame el numero como texto."
            )

    elif msg_type == "location":
        loc = message.get("location", {})
        lat = loc.get("latitude")
        lng = loc.get("longitude")
        loc_name = loc.get("name", "")
        loc_address = loc.get("address", "")

        if lat is not None and lng is not None:
            state.user_latitude = float(lat)
            state.user_longitude = float(lng)
            state.updated_at = datetime.now(timezone.utc)

            # If awaiting a search, auto-trigger with the location
            if (
                state.status == ConversationStatus.AWAITING_PROVIDER
                and state.pending_intent == IntentType.SEARCH_PROVIDERS
                and state.pending_entities
            ):
                service = state.pending_entities.service_type or ""
                location_hint = loc_name or loc_address or ""
                query = f"{service} {location_hint}".strip() or service
                if query:
                    try:
                        results = await search_places(
                            query,
                            latitude=state.user_latitude,
                            longitude=state.user_longitude,
                        )
                        state.search_results = results
                        msg = format_search_results(results, language=state.language.value)
                        await _send_and_track(state, from_number, msg)
                    except Exception:
                        logger.exception("Places search failed after location share")
            else:
                lang = state.language.value
                ack = "Listo, tengo tu ubicacion." if lang == "es" else "Got your location."
                await _send_and_track(state, from_number, ack)

    elif msg_type == "text":
        body = message.get("text", {}).get("body", "")
        logger.info("Text body: %s", body[:100] if body else "<empty>")
        add_message(state, "user", body)
        try:
            result = await extract_intent(body, context=context)
            await _process_intent(state, result, from_number)
            if result.intent == IntentType.SEARCH_PROVIDERS and result.entities.location and result.confidence >= 0.8:
                query = f"{result.entities.service_type or ''} {result.entities.location}".strip()
                if query:
                    try:
                        results = await search_places(
                            query,
                            latitude=state.user_latitude,
                            longitude=state.user_longitude,
                        )
                        state.search_results = results
                        msg = format_search_results(results, language=state.language.value)
                        await _send_and_track(state, from_number, msg)
                    except Exception:
                        logger.exception("Places search failed")
        except Exception:
            logger.exception("Intent parsing failed")
            await send_whatsapp_message(from_number, "Perdon, tuve un error. Intenta de nuevo.")

    elif msg_type == "audio":
        media_id = message.get("audio", {}).get("id", "")
        if media_id:
            try:
                audio_bytes = await download_whatsapp_media(media_id)
                transcription = await transcribe_audio(audio_bytes)
                add_message(state, "user", f"[audio] {transcription.text}")
                result = await extract_intent(transcription.text, context=context)
                await _process_intent(state, result, from_number)
                if result.intent == IntentType.SEARCH_PROVIDERS and result.entities.location and result.confidence >= 0.8:
                    query = f"{result.entities.service_type or ''} {result.entities.location}".strip()
                    if query:
                        try:
                            results = await search_places(
                                query,
                                latitude=state.user_latitude,
                                longitude=state.user_longitude,
                            )
                            state.search_results = results
                            msg = format_search_results(results, language=state.language.value)
                            await _send_and_track(state, from_number, msg)
                        except Exception:
                            logger.exception("Places search failed")
            except Exception:
                logger.exception("Failed to process voice note")
                await send_whatsapp_message(
                    from_number, "No pude procesar el audio. Intenta de nuevo o mandame texto."
                )

    # Trigger outbound call if state is CALLING and we have a number
    if state.status == ConversationStatus.CALLING and state.provider_phone and not state.active_call_ids:
        await _trigger_call(from_number, state)


# --- Webhook endpoints ---


@router.get("/whatsapp")
async def whatsapp_verify(request: Request):
    """Meta webhook verification (hub.challenge)."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == settings.meta_webhook_verify_token:
        logger.info("Webhook verified successfully")
        return Response(content=challenge, media_type="text/plain")

    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    """Meta WhatsApp Cloud API webhook — receives incoming messages."""
    body = await request.json()

    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})

            if "messages" not in value:
                continue

            messages = value.get("messages", [])
            contacts_info = value.get("contacts", [])
            profile_name = (
                contacts_info[0].get("profile", {}).get("name", "")
                if contacts_info
                else ""
            )

            for message in messages:
                msg_id = message.get("id", "")
                if msg_id in _seen_message_ids:
                    continue
                _seen_message_ids.add(msg_id)
                # Cap dedup set size
                if len(_seen_message_ids) > 500:
                    _seen_message_ids.clear()
                from_number = message.get("from", "")
                asyncio.create_task(_handle_message(from_number, profile_name, message))

    return {"status": "ok"}
