import asyncio
import logging

from fastapi import APIRouter, Request

from app.services.calendar import build_calendar_link
from app.services.elevenlabs_call import fetch_conversation_details, pop_call
from app.services.messages import format_call_failed, format_multi_call_update, format_ranked_results, format_summary_message, generate_smart_summary
from app.services.ranking import rank_results
from app.services.state import ConversationStatus, MultiCallCampaign, MultiCallProvider, find_state_by_conversation_id
from app.services.twilio import send_whatsapp_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["callbacks"])


def _find_campaign_provider(campaign: MultiCallCampaign, call_sid: str, conversation_id: str | None) -> MultiCallProvider | None:
    """Match a call to its campaign provider by call_sid or conversation_id."""
    for p in campaign.providers:
        if call_sid and call_sid == p.call_sid:
            return p
        if conversation_id and conversation_id == p.conversation_id:
            return p
    return None


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

            if state.multi_call:
                provider = _find_campaign_provider(state.multi_call, call_sid, pop_call(call_sid))
                name = provider.name if provider else "?"
                msg = format_multi_call_update(name, call_status, language=lang)
                await send_whatsapp_message(phone, msg)
                state.multi_call.results.append({
                    "provider_name": name,
                    "phone": provider.phone if provider else "",
                    "rating": provider.rating if provider else None,
                    "total_ratings": provider.total_ratings if provider else 0,
                    "summary": None,
                    "outcome": call_status,
                })
                state.multi_call.pending_count -= 1
                # Check if all calls done
                if state.multi_call.pending_count <= 0:
                    ranked = rank_results(state.multi_call.results)
                    msg = format_ranked_results(ranked, language=lang)
                    await send_whatsapp_message(phone, msg)
                    state.status = ConversationStatus.COMPLETED
                    state.multi_call = None
            else:
                msg = format_call_failed(state.provider_name, language=lang)
                await send_whatsapp_message(phone, msg)
                state.status = ConversationStatus.COMPLETED
                state.call_results.append({
                    "provider": state.provider_name,
                    "outcome": call_status,
                })
                pop_call(call_sid)
        else:
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

            if state.multi_call:
                # --- Multi-call flow ---
                provider = _find_campaign_provider(state.multi_call, call_sid, conversation_id)
                name = provider.name if provider else "?"
                provider_phone = provider.phone if provider else ""
                summary_result = None
                if conv_data:
                    summary_result = await generate_smart_summary(name, provider_phone, conv_data, language=lang)

                state.multi_call.results.append({
                    "provider_name": name,
                    "phone": provider_phone,
                    "rating": provider.rating if provider else None,
                    "total_ratings": provider.total_ratings if provider else 0,
                    "summary": summary_result,
                    "conversation_id": conversation_id,
                    "outcome": "completed",
                })
                state.multi_call.pending_count -= 1

                # When ALL calls done → rank and send consolidated message
                if state.multi_call.pending_count <= 0:
                    ranked = rank_results(state.multi_call.results)
                    msg = format_ranked_results(ranked, language=lang)
                    await send_whatsapp_message(phone, msg)

                    # Calendar link for best confirmed booking
                    best_booked = next(
                        (r for r in ranked if r.get("summary") and r["summary"].booking_confirmed),
                        None,
                    )
                    if best_booked and best_booked["summary"].date and best_booked["summary"].time:
                        s = best_booked["summary"]
                        cal_link = await build_calendar_link(
                            summary=f"Turno: {s.provider_name or best_booked['provider_name']}",
                            start_date=s.date,
                            start_time=s.time,
                            duration_minutes=s.duration_minutes or 60,
                            location=s.address,
                        )
                        if lang == "es":
                            await send_whatsapp_message(phone, f"Agrega el turno a tu calendario: {cal_link}")
                        else:
                            await send_whatsapp_message(phone, f"Add the appointment to your calendar: {cal_link}")

                    state.status = ConversationStatus.COMPLETED
                    state.multi_call = None
            else:
                # --- Single-call flow ---
                display_name = state.provider_name or state.provider_phone or "?"
                if conv_data:
                    summary_result = await generate_smart_summary(display_name, state.provider_phone, conv_data, language=lang)

                    msg = format_summary_message(summary_result, display_name, language=lang)
                    await send_whatsapp_message(phone, msg)

                    # Calendar link as separate message after summary
                    if summary_result.booking_confirmed and summary_result.date and summary_result.time:
                        cal_link = await build_calendar_link(
                            summary=f"Turno: {summary_result.provider_name or display_name}",
                            start_date=summary_result.date,
                            start_time=summary_result.time,
                            duration_minutes=summary_result.duration_minutes or 60,
                            location=summary_result.address,
                        )
                        cal_msg = (
                            f"Agrega el turno a tu calendario: {cal_link}"
                            if lang == "es"
                            else f"Add the appointment to your calendar: {cal_link}"
                        )
                        await send_whatsapp_message(phone, cal_msg)
                    state.call_results.append({
                        "provider": state.provider_name,
                        "outcome": "completed",
                        "conversation_id": conversation_id,
                    })
                if state.status != ConversationStatus.COMPLETED:
                    state.status = ConversationStatus.COMPLETED

    return {"status": "ok"}
