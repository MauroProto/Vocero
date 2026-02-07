"""ElevenLabs voice agent server tool webhooks.

Each endpoint is called mid-conversation by the Phone Agent.
Responses must be fast (< 500ms) to maintain voice latency.
"""

import logging

from fastapi import APIRouter

from app.schemas.tools import (
    CheckPreferenceRequest,
    CheckPreferenceResponse,
    ConfirmBookingRequest,
    EndCallRequest,
    ReportSlotsRequest,
)
from app.services.messages import (
    format_booking_confirmed,
    format_no_availability,
    format_slots_available,
)
from app.services.state import ConversationStatus, find_state_by_conversation_id
from app.services.twilio import send_whatsapp_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.post("/report_available_slots")
async def report_available_slots(req: ReportSlotsRequest):
    """Agent reports slots offered by the provider."""
    logger.info("report_available_slots: conv=%s slots=%s", req.conversation_id, req.slots)

    result = find_state_by_conversation_id(req.conversation_id)
    if result:
        phone, state = result
        lang = state.language.value
        msg = format_slots_available(state.provider_name, language=lang)
        await send_whatsapp_message(phone, msg)

    return {"status": "ok", "slots_received": len(req.slots)}


@router.post("/check_user_preference")
async def check_user_preference(req: CheckPreferenceRequest):
    """Validate a proposed slot against the user's time preference."""
    logger.info("check_user_preference: conv=%s proposed=%s %s", req.conversation_id, req.proposed_date, req.proposed_time)

    result = find_state_by_conversation_id(req.conversation_id)
    if not result:
        return CheckPreferenceResponse(accept=True, reason="No preference on file, accept any slot.")

    _, state = result
    entities = state.pending_entities
    if not entities or not (entities.date_preference or entities.time_preference):
        return CheckPreferenceResponse(accept=True, reason="User has no specific time preference.")

    pref_parts = []
    if entities.date_preference:
        pref_parts.append(entities.date_preference)
    if entities.time_preference:
        pref_parts.append(entities.time_preference)
    pref = ", ".join(pref_parts)

    return CheckPreferenceResponse(
        accept=True,
        reason=f"User prefers: {pref}. Proposed: {req.proposed_date} {req.proposed_time}. Please confirm with user if close match.",
    )


@router.post("/confirm_booking")
async def confirm_booking(req: ConfirmBookingRequest):
    """Record a confirmed appointment and notify user via WhatsApp."""
    date_time = f"{req.date} {req.time}"
    logger.info("confirm_booking: conv=%s datetime=%s", req.conversation_id, date_time)

    result = find_state_by_conversation_id(req.conversation_id)
    if result:
        phone, state = result
        lang = state.language.value
        provider = req.provider_name or state.provider_name
        msg = format_booking_confirmed(
            provider_name=provider,
            date_time=date_time,
            notes=req.notes,
            language=lang,
        )
        await send_whatsapp_message(phone, msg)
        state.status = ConversationStatus.COMPLETED
        state.call_results.append({
            "provider": provider,
            "datetime": date_time,
            "notes": req.notes,
            "outcome": "booked",
        })

    return {"status": "ok", "booking_confirmed": True}


@router.post("/end_call_no_availability")
async def end_call_no_availability(req: EndCallRequest):
    """Mark provider as unavailable and notify user."""
    logger.info("end_call_no_availability: conv=%s reason=%s", req.conversation_id, req.reason)

    result = find_state_by_conversation_id(req.conversation_id)
    if result:
        phone, state = result
        lang = state.language.value
        msg = format_no_availability(state.provider_name, language=lang)
        await send_whatsapp_message(phone, msg)
        state.status = ConversationStatus.COMPLETED
        state.call_results.append({
            "provider": state.provider_name,
            "outcome": "no_availability",
            "reason": req.reason,
        })

    return {"status": "ok", "call_ended": True}
