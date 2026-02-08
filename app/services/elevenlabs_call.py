"""Outbound calls via ElevenLabs register-call + Twilio.

Uses ElevenLabs register-call endpoint to get TwiML that connects
Twilio directly to ElevenLabs WebSocket (no manual audio bridge).
"""

import json
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Track active calls: call_sid -> conversation_id
_active_calls: dict[str, str] = {}


async def make_outbound_call(
    to_number: str,
    dynamic_variables: dict[str, str] | None = None,
    language: str = "es",
) -> tuple[str, str]:
    """Place outbound call via ElevenLabs register-call + Twilio.

    1. Register call with ElevenLabs → get TwiML (points to ElevenLabs WS)
    2. Create Twilio call with that TwiML
    3. Twilio connects directly to ElevenLabs (handles audio natively)
    """
    # Pick agent based on language
    agent_id = settings.elevenlabs_agent_id_en if language == "en" else settings.elevenlabs_agent_id
    logger.info("Using %s agent: %s", language, agent_id)

    # Step 1: Register call with ElevenLabs
    register_body: dict = {
        "agent_id": agent_id,
        "from_number": settings.twilio_phone_number,
        "to_number": to_number,
        "direction": "outbound",
    }
    if dynamic_variables:
        register_body["conversation_initiation_client_data"] = {
            "dynamic_variables": dynamic_variables,
        }

    async with httpx.AsyncClient() as client:
        reg_resp = await client.post(
            "https://api.elevenlabs.io/v1/convai/twilio/register-call",
            headers={
                "xi-api-key": settings.elevenlabs_api_key,
                "Content-Type": "application/json",
            },
            json=register_body,
        )
        reg_resp.raise_for_status()
        twiml = reg_resp.text

    logger.info("ElevenLabs register-call OK, got TwiML (%d bytes)", len(twiml))

    # Extract conversation_id from TwiML parameter if present
    conversation_id = ""
    if 'name="conversation_id"' in twiml:
        import re
        match = re.search(r'name="conversation_id"\s+value="([^"]+)"', twiml)
        if match:
            conversation_id = match.group(1)
            logger.info("Conversation ID from TwiML: %s", conversation_id)

    # Step 2: Create Twilio call with ElevenLabs TwiML
    callback_url = f"{settings.app_base_url}/api/call-status"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Calls.json",
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            data={
                "To": to_number,
                "From": settings.twilio_phone_number,
                "Twiml": twiml,
                "StatusCallback": callback_url,
                "StatusCallbackEvent": "completed",
            },
        )
        resp.raise_for_status()
        call_data = resp.json()
        call_sid = call_data.get("sid", "")

    if conversation_id and call_sid:
        _active_calls[call_sid] = conversation_id

    logger.info("Outbound call: sid=%s conv=%s to=%s", call_sid, conversation_id, to_number)
    return conversation_id, call_sid


def get_conversation_id(call_sid: str) -> str | None:
    """Look up ElevenLabs conversation ID for an active call."""
    return _active_calls.get(call_sid)


def pop_call(call_sid: str) -> str | None:
    """Remove and return conversation_id for a finished call."""
    return _active_calls.pop(call_sid, None)


async def fetch_conversation_details(conversation_id: str) -> dict | None:
    """Fetch conversation transcript and analysis from ElevenLabs."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.elevenlabs.io/v1/convai/conversations/{conversation_id}",
            headers={"xi-api-key": settings.elevenlabs_api_key},
            timeout=15.0,
        )
        if resp.status_code != 200:
            logger.warning("Failed to fetch conversation %s: %s", conversation_id, resp.status_code)
            return None
        return resp.json()
