import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

GRAPH_API_URL = "https://graph.facebook.com/v21.0"


def _normalize_ar_number(phone: str) -> str:
    """Argentine mobile numbers: Meta sends 549XX but requires 54XX to send back."""
    if phone.startswith("549") and len(phone) == 13:
        return "54" + phone[3:]
    return phone


async def send_whatsapp_message(to: str, body: str) -> str:
    """Send a WhatsApp message via Meta Cloud API. Returns message ID."""
    to = _normalize_ar_number(to)
    url = f"{GRAPH_API_URL}/{settings.meta_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.meta_access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        msg_id = data.get("messages", [{}])[0].get("id", "")

    logger.info("Sent WhatsApp to %s: %s", to, msg_id)
    return msg_id


async def download_whatsapp_media(media_id: str) -> bytes:
    """Download media from Meta's WhatsApp Cloud API (2-step: get URL, then download)."""
    headers = {"Authorization": f"Bearer {settings.meta_access_token}"}
    async with httpx.AsyncClient() as client:
        # Step 1: Get the media URL
        resp = await client.get(f"{GRAPH_API_URL}/{media_id}", headers=headers)
        resp.raise_for_status()
        media_url = resp.json()["url"]

        # Step 2: Download the actual file
        resp = await client.get(media_url, headers=headers)
        resp.raise_for_status()
        return resp.content
