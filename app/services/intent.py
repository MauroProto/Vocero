import logging

import httpx

from app.config import settings
from app.schemas.intent import IntentResult

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None

SYSTEM_PROMPT = """\
You are a bilingual (English/Spanish) intent classifier for a WhatsApp appointment-booking assistant called Vocero.

Analyze the user's message and extract:

## Intents
- **call_number**: User provided a phone number and wants to call a provider.
- **request_appointment**: User describes a service need but hasn't provided a provider's phone number yet. Ask them for a contact or phone number.
- **confirm**: User is confirming a prior suggestion or answering yes to a question.
- **cancel**: User wants to stop or cancel the current flow.
- **help**: Message is unclear, or user is asking for help/instructions.

## Entities (extract when present)
- phone_number: Phone number in any format (e.g., +5491112345678, 11-2233-4455)
- provider_name: Name of the business or professional
- service_type: Type of service (dentist, haircut, mechanic, etc.)
- date_preference: Preferred date (tomorrow, Friday, next week, etc.)
- time_preference: Preferred time (morning, 3pm, between 2 and 4, etc.)
- location: Location preference
- special_requests: Any special notes or requests

## Language Detection
- Detect whether the message is in English ("en") or Spanish ("es").

## Response Message
- Generate a short, helpful reply in the SAME language as the user's message.
- For **request_appointment**: acknowledge what they need and ask for the provider's phone number or contact.
- For **call_number**: confirm you'll call the number and for what service.
- For **confirm**: acknowledge the confirmation.
- For **cancel**: confirm the cancellation.
- For **help**: briefly explain what Vocero can do (book appointments by calling providers).

## Conversation Context
If conversation context is provided, use it to interpret the user's message as a follow-up. For example:
- A time reference like "between 2 and 4" should fill time_preference if a prior appointment request is in context.
- "yes" or "sí" should be classified as **confirm** if the bot previously asked a question.
- Use context to fill in entities that were established in prior messages.

## Confidence
- Set confidence between 0.0 and 1.0 based on how certain you are about the intent classification.
- Clear, unambiguous messages: 0.85-1.0
- Somewhat ambiguous: 0.5-0.84
- Very unclear: below 0.5
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
            "model": "gpt-4.1-mini",
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
