import asyncio
import logging

from fastapi import APIRouter, Request

from app.services.elevenlabs_call import fetch_conversation_details, pop_call
from app.services.messages import format_call_failed, generate_smart_summary
from app.services.state import ConversationStatus, find_state_by_conversation_id
from app.services.twilio import send_whatsapp_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["callbacks"])


@router.post("/call-status")
async def call_status_callback(request: Request):
    """Twilio call status webhook — receives updates as calls progress."""
    form = await request.form()
    call_sid = str(form.get("CallSid", ""))
    call_status = str(form.get("CallStatus", ""))

    logger.info("Call status callback: sid=%s status=%s", call_sid, call_status)

    if call_status in ("failed", "busy", "no-answer"):
        result = find_state_by_conversation_id(call_sid)
        if result:
            phone, state = result
            lang = state.language.value
            msg = format_call_failed(state.provider_name, language=lang)
            await send_whatsapp_message(phone, msg)
            state.status = ConversationStatus.COMPLETED
            state.call_results.append({
                "provider": state.provider_name,
                "outcome": call_status,
            })
        pop_call(call_sid)

    elif call_status == "completed":
        # Look up conversation_id and user state
        conversation_id = pop_call(call_sid)
        result = find_state_by_conversation_id(call_sid) or (
            find_state_by_conversation_id(conversation_id) if conversation_id else None
        )

        if result and conversation_id:
            phone, state = result
            lang = state.language.value
            state.last_conversation_id = conversation_id
            # Wait for ElevenLabs to finalize the conversation
            await asyncio.sleep(5)
            conv_data = await fetch_conversation_details(conversation_id)
            if conv_data:
                msg = await generate_smart_summary(state.provider_name, state.provider_phone, conv_data, language=lang)
                await send_whatsapp_message(phone, msg)
                state.call_results.append({
                    "provider": state.provider_name,
                    "outcome": "completed",
                    "conversation_id": conversation_id,
                })
            if state.status != ConversationStatus.COMPLETED:
                state.status = ConversationStatus.COMPLETED

    return {"status": "ok"}
