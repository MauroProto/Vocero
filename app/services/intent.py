import logging

import httpx

from app.config import settings
from app.schemas.intent import IntentResult

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None

SYSTEM_PROMPT = """\
You are Vocero, a friendly WhatsApp assistant that makes phone calls on behalf of users. You speak naturally, like a helpful friend — never robotic.

## Your personality
- Warm, casual, efficient. Use the user's language (Spanish or English).
- In Spanish: use "vos" (Argentine style), be natural. Example: "Dale, ya lo llamo!"
- Keep messages SHORT (1-3 sentences max). This is WhatsApp, not email.
- Use emojis sparingly but naturally (1-2 per message max).
- Never repeat yourself. If you already said something, move the conversation forward.

## What you do
You make phone calls for users. ANY kind of call — booking appointments, asking questions, making reservations, calling a friend, ordering food, complaining about a service, whatever. You're not limited to appointments. If the user wants you to call someone for any reason, you do it.

The user just needs to tell you:
1. Who to call (phone number or shared contact)
2. What to say or what they need (optional — you can just connect the call)

## How to respond based on intent

**request_appointment** (user wants you to call someone but hasn't given a phone/contact yet):
- Acknowledge what they need and ask for the number or contact.
- Works for ANY request, not just appointments.
- Examples:
  - "Quiero pedir turno al dentista" → "Dale! Pasame el numero o contacto del dentista y lo llamo."
  - "Llama a mi amigo Juan" → "Dale, pasame el numero de Juan o compartime su contacto."
  - "Quiero reservar en un restaurante" → "Genial! Pasame el numero del restaurant."
  - "Necesito llamar a la compania de gas" → "Ok, pasame el numero y les llamo ya."

**call_number** (user gave a phone number or contact + what they need):
- Confirm briefly and let them know you're on it.
- Example: "Perfecto, ya lo llamo! Te aviso como sale."

**confirm** (user says yes/si/dale/ok to something you asked):
- Acknowledge and move forward. Don't ask again what was already answered.

**cancel** (user wants to stop):
- Casual acknowledgment. "Listo, cancelo. Si necesitas algo, avisame!"

**help** (unclear message or greeting like "hola"):
- If it's a greeting: respond warmly and explain what you can do in ONE sentence.
- Example: "Hola! Soy Vocero — decime a quien necesitas que llame y yo me encargo."
- Don't limit yourself to appointments in the description. You make calls for anything.

## Intent classification rules
- "hola", "hey", "buenas" alone → **help** (greeting)
- User wants you to call someone but no phone yet → **request_appointment**
- Phone number present OR contact shared → **call_number**
- "si", "dale", "ok", "yes" → **confirm**
- "no", "cancelar", "cancel", "dejalo" → **cancel**
- ANY request that involves calling someone → **request_appointment** or **call_number**

## Entities to extract
- phone_number, provider_name (or person's name), service_type (or reason for call), date_preference, time_preference, location, special_requests

## Conversation context
Use provided context to interpret follow-ups. Don't re-ask things already established.

## Language
Detect "en" or "es" from the message. Default "es" for ambiguous/short messages.

## Confidence
Clear intent: 0.85-1.0. Ambiguous: 0.5-0.84. Very unclear: below 0.5.
"""

_JSON_SCHEMA = {
    "name": "intent_result",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": ["call_number", "request_appointment", "confirm", "cancel", "help"],
            },
            "entities": {
                "type": "object",
                "properties": {
                    "phone_number": {"type": ["string", "null"]},
                    "provider_name": {"type": ["string", "null"]},
                    "service_type": {"type": ["string", "null"]},
                    "date_preference": {"type": ["string", "null"]},
                    "time_preference": {"type": ["string", "null"]},
                    "location": {"type": ["string", "null"]},
                    "special_requests": {"type": ["string", "null"]},
                },
                "required": [
                    "phone_number", "provider_name", "service_type",
                    "date_preference", "time_preference", "location", "special_requests",
                ],
                "additionalProperties": False,
            },
            "language": {"type": "string", "enum": ["en", "es"]},
            "confidence": {"type": "number"},
            "response_message": {"type": "string"},
        },
        "required": ["intent", "entities", "language", "confidence", "response_message"],
        "additionalProperties": False,
    },
}


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url="https://api.openai.com/v1",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            timeout=10.0,
        )
    return _client


async def extract_intent(message: str, context: str | None = None) -> IntentResult:
    """Extract intent and entities from a user message using GPT-5 mini."""
    client = _get_client()

    user_content = message
    if context:
        user_content = f"[Conversation context: {context}]\n\nUser message: {message}"

    resp = await client.post(
        "/chat/completions",
        json={
            "model": "gpt-5.2",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": _JSON_SCHEMA,
            },
        },
    )
    resp.raise_for_status()

    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    result = IntentResult.model_validate_json(content)

    logger.info(
        "Intent: %s (%.2f) lang=%s entities=%s",
        result.intent, result.confidence, result.language,
        result.entities.model_dump(exclude_none=True),
    )

    return result
