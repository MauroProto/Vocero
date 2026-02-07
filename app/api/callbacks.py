import logging

from fastapi import APIRouter, Request

from app.services.messages import format_call_failed
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

    return {"status": "ok"}
