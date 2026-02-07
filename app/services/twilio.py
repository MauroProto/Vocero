import logging

from twilio.rest import Client

from app.config import settings

logger = logging.getLogger(__name__)

_client: Client | None = None


def get_twilio_client() -> Client:
    global _client
    if _client is None:
        _client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    return _client


async def send_whatsapp_message(to: str, body: str) -> str:
    """Send a WhatsApp message via Twilio REST API. Returns message SID."""
    client = get_twilio_client()
    message = client.messages.create(
        from_=settings.twilio_whatsapp_number,
        to=to,
        body=body,
    )
    logger.info("Sent WhatsApp message %s to %s", message.sid, to)
    return message.sid
