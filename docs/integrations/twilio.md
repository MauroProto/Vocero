# Twilio Integration Guide

## WhatsApp Webhook

### Incoming Messages

Twilio sends `POST application/x-www-form-urlencoded` to your webhook URL.

**Key parameters:**

| Parameter | Example | Description |
|-----------|---------|-------------|
| `From` | `whatsapp:+14155238886` | Sender's WhatsApp number |
| `Body` | `"I need a dentist"` | Message text |
| `NumMedia` | `0` or `1` | Number of media attachments |
| `MediaUrl0` | `https://api.twilio.com/...` | URL to download media |
| `MediaContentType0` | `audio/ogg` | MIME type (voice notes = `audio/ogg`) |
| `ProfileName` | `"John Doe"` | WhatsApp display name |
| `MessageSid` | `SM1234...` | Unique message ID |

### Webhook Handler Pattern

```python
from fastapi import APIRouter, Request, Response
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator

@router.post("/api/whatsapp")
async def whatsapp_webhook(request: Request):
    form_data = await request.form()

    from_number = form_data.get("From")
    body = form_data.get("Body", "")
    num_media = int(form_data.get("NumMedia", 0))

    if num_media > 0:
        media_url = form_data.get("MediaUrl0")
        media_type = form_data.get("MediaContentType0")
        # Handle voice note (audio/ogg)
    else:
        # Handle text message
        pass

    response = MessagingResponse()
    response.message("Got it! Working on your request...")
    return Response(content=str(response), media_type="application/xml")
```

### Signature Validation

```python
validator = RequestValidator(settings.twilio_auth_token)
is_valid = validator.validate(
    uri=str(request.url),
    params=dict(await request.form()),
    signature=request.headers.get("X-Twilio-Signature", "")
)
```

**Gotcha:** URI must match exactly what Twilio sees. Behind ngrok/proxy, watch for http vs https mismatch.

### Sending Messages (REST API)

For async responses (not in webhook response):

```python
from twilio.rest import Client

client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

message = client.messages.create(
    from_=settings.twilio_whatsapp_number,
    to="whatsapp:+14155238886",
    body="*Appointment Confirmed*\n\n"
         "*Provider:* Dr. Smith\n"
         "*Date:* Monday, Feb 10\n"
         "*Time:* 2:30 PM"
)
```

**WhatsApp formatting:** `*bold*`, `_italic_`, `~strikethrough~`, newlines with `\n`.

**24-hour window:** Free-form messages only within 24h of last user message. Outside this, use template messages.

## Voice Notes

WhatsApp voice notes arrive as `audio/ogg` (Opus codec).

**Download pattern:**
```python
import httpx

async def download_voice_note(media_url: str) -> bytes:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            media_url,
            auth=(settings.twilio_account_sid, settings.twilio_auth_token)
        )
        return response.content  # OGG bytes
```

Most transcription APIs (OpenAI Whisper, ElevenLabs) accept OGG directly.

## Outbound Calls

### With ElevenLabs Native Integration

No Twilio call code needed — ElevenLabs handles it via their outbound-call API. See `docs/integrations/elevenlabs.md`.

### Call Status Callbacks

Subscribe to status events when initiating calls:

| Status | Meaning |
|--------|---------|
| `initiated` | Twilio dialed the number |
| `ringing` | Remote phone is ringing |
| `answered` | Call picked up |
| `completed` | Call finished normally |
| `busy` | Line was busy |
| `no-answer` | No one picked up |
| `failed` | Could not connect |

```python
@router.post("/api/call-status")
async def call_status_callback(request: Request):
    form_data = await request.form()
    call_sid = form_data.get("CallSid")
    status = form_data.get("CallStatus")
    duration = form_data.get("CallDuration")
    # Update call record in DB
```

## Parallel Calls

- **CPS (Calls Per Second):** Default 1 CPS. Initiating 15 calls takes ~15 seconds.
- **Concurrent calls:** No Twilio-side limit on active concurrent calls.
- **For hackathon:** 3-5 parallel calls is the sweet spot. All will be active simultaneously once connected.

## Dev Setup

1. Create Twilio account + get WhatsApp Sandbox number
2. Run `ngrok http 8000` for local webhook exposure
3. Set ngrok URL as webhook in Twilio Console → Messaging → WhatsApp Sandbox
4. For outbound calls: buy a Twilio phone number with voice capability
