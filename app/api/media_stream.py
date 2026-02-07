"""WebSocket endpoint for Twilio Media Stream ↔ ElevenLabs bridge."""

import base64
import json
import logging

from fastapi import APIRouter, WebSocket

from app.services.elevenlabs_call import bridge_call

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["media-stream"])


@router.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    """Handle Twilio Media Stream and bridge audio to ElevenLabs."""
    await websocket.accept()

    call_sid = "unknown"
    stream_sid = ""
    dynamic_variables: dict[str, str] = {}

    try:
        # Twilio sends 'connected' then 'start' — read both before bridging
        while True:
            msg = await websocket.receive_text()
            data = json.loads(msg)
            event = data.get("event")

            if event == "connected":
                logger.info("Twilio WebSocket connected")
                continue

            if event == "start":
                start_info = data.get("start", {})
                call_sid = start_info.get("callSid", "unknown")
                stream_sid = start_info.get("streamSid", "")

                # Decode dynamic variables from custom parameters
                custom = start_info.get("customParameters", {})
                dv_encoded = custom.get("dv", "")
                if dv_encoded:
                    try:
                        dynamic_variables = json.loads(base64.b64decode(dv_encoded))
                    except Exception:
                        logger.warning("Failed to decode dynamic_variables")

                logger.info("Stream started: call=%s stream=%s", call_sid, stream_sid)
                break

        # Now bridge the remaining audio between Twilio ↔ ElevenLabs
        await bridge_call(websocket, call_sid, stream_sid, dynamic_variables)

    except Exception:
        logger.exception("Media stream error: call=%s", call_sid)
    finally:
        logger.info("Media stream closed: call=%s", call_sid)
