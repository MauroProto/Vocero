"""Outbound calls via manual Twilio→ElevenLabs WebSocket bridge.

Creates Twilio call with custom TwiML, bridges audio between
Twilio Media Stream and ElevenLabs Conversational AI WebSocket.
"""

import asyncio
import base64
import json
import logging

import httpx
import websockets
from starlette.websockets import WebSocketDisconnect

from app.config import settings

logger = logging.getLogger(__name__)

# Track active bridges: call_sid -> conversation_id
_active_bridges: dict[str, str] = {}


async def _get_signed_url() -> str:
    """Get a signed WebSocket URL from ElevenLabs."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.elevenlabs.io/v1/convai/conversation/get-signed-url",
            params={"agent_id": settings.elevenlabs_agent_id},
            headers={"xi-api-key": settings.elevenlabs_api_key},
        )
        resp.raise_for_status()
        return resp.json()["signed_url"]


async def bridge_call(
    twilio_ws,
    call_sid: str,
    stream_sid: str,
    dynamic_variables: dict[str, str] | None = None,
) -> None:
    """Bridge audio between Twilio Media Stream and ElevenLabs WebSocket."""
    signed_url = await _get_signed_url()
    conversation_id = None

    try:
        async with websockets.connect(signed_url) as eleven_ws:
            # Configure audio format for Twilio Media Streams (mulaw 8kHz)
            init_msg: dict = {
                "type": "conversation_initiation_client_data",
                "conversation_config_override": {
                    "agent": {
                        "prompt": {},
                        "first_message": None,
                        "language": dynamic_variables.get("language", "es") if dynamic_variables else "es",
                    },
                    "asr": {
                        "user_input_audio_format": "ulaw_8000",
                    },
                    "tts": {
                        "agent_output_audio_format": "ulaw_8000",
                    },
                },
            }
            if dynamic_variables:
                init_msg["dynamic_variables"] = dynamic_variables

            await eleven_ws.send(json.dumps(init_msg))
            logger.info("ElevenLabs WS connected, init sent for call %s", call_sid)

            async def twilio_to_eleven():
                """Forward Twilio audio → ElevenLabs."""
                try:
                    async for message in twilio_ws.iter_text():
                        data = json.loads(message)
                        event = data.get("event")

                        if event == "media":
                            payload = data.get("media", {}).get("payload", "")
                            if payload:
                                await eleven_ws.send(json.dumps({
                                    "user_audio_chunk": payload,
                                }))

                        elif event == "stop":
                            logger.info("Twilio stream stopped for call %s", call_sid)
                            break
                except Exception:
                    logger.exception("twilio_to_eleven error")

            async def eleven_to_twilio():
                """Forward ElevenLabs audio → Twilio."""
                nonlocal conversation_id
                try:
                    async for message in eleven_ws:
                        data = json.loads(message)
                        msg_type = data.get("type")

                        if msg_type == "conversation_initiation_metadata":
                            conversation_id = data.get("conversation_id", "")
                            if conversation_id:
                                _active_bridges[call_sid] = conversation_id
                            logger.info("ElevenLabs conversation: %s", conversation_id)

                        elif msg_type == "audio":
                            # Handle both possible audio field formats
                            audio_data = data.get("audio", {}).get("chunk", "")
                            if not audio_data:
                                audio_data = data.get("audio_event", {}).get("audio_base_64", "")
                            if audio_data and stream_sid:
                                try:
                                    await twilio_ws.send_json({
                                        "event": "media",
                                        "streamSid": stream_sid,
                                        "media": {"payload": audio_data},
                                    })
                                except WebSocketDisconnect:
                                    logger.info("Twilio WS gone during audio send for call %s", call_sid)
                                    break

                        elif msg_type == "interruption":
                            if stream_sid:
                                try:
                                    await twilio_ws.send_json({
                                        "event": "clear",
                                        "streamSid": stream_sid,
                                    })
                                except WebSocketDisconnect:
                                    break

                        elif msg_type == "ping":
                            event_id = data.get("ping_event", {}).get("event_id")
                            if event_id:
                                await eleven_ws.send(json.dumps({
                                    "type": "pong",
                                    "event_id": event_id,
                                }))

                        elif msg_type == "agent_response":
                            text = data.get("agent_response_event", {}).get("agent_response", "")
                            logger.info("[Agent] %s", text[:150])

                        elif msg_type == "user_transcript":
                            text = data.get("user_transcription_event", {}).get("user_transcript", "")
                            logger.info("[User] %s", text[:150])

                        else:
                            # Log unknown message types for debugging
                            if msg_type not in ("internal_vad_score", "internal_turn_probability"):
                                logger.debug("ElevenLabs msg: type=%s keys=%s", msg_type, list(data.keys()))

                except websockets.exceptions.ConnectionClosed:
                    logger.info("ElevenLabs WS closed for call %s", call_sid)
                except WebSocketDisconnect:
                    logger.info("Twilio WS disconnected for call %s", call_sid)
                except Exception:
                    logger.exception("eleven_to_twilio error")

            await asyncio.gather(twilio_to_eleven(), eleven_to_twilio())

    except Exception:
        logger.exception("Bridge error for call %s", call_sid)
    finally:
        _active_bridges.pop(call_sid, None)
        logger.info("Bridge closed: call=%s conv=%s", call_sid, conversation_id)


async def make_outbound_call(
    to_number: str,
    dynamic_variables: dict[str, str] | None = None,
) -> tuple[str, str]:
    """Place outbound call via Twilio with TwiML pointing to our WebSocket bridge."""
    base_url = settings.app_base_url
    ws_url = base_url.replace("https://", "wss://").replace("http://", "wss://")

    dv_encoded = base64.b64encode(json.dumps(dynamic_variables or {}).encode()).decode()

    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        "<Connect>"
        f'<Stream url="{ws_url}/api/media-stream">'
        f'<Parameter name="dv" value="{dv_encoded}" />'
        "</Stream>"
        "</Connect>"
        "</Response>"
    )

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Calls.json",
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            data={
                "To": to_number,
                "From": settings.twilio_phone_number,
                "Twiml": twiml,
            },
        )
        resp.raise_for_status()
        call_data = resp.json()
        call_sid = call_data.get("sid", "")

    logger.info("Outbound call: sid=%s to=%s", call_sid, to_number)
    return "", call_sid


def get_conversation_id(call_sid: str) -> str | None:
    """Look up ElevenLabs conversation ID for an active call."""
    return _active_bridges.get(call_sid)
