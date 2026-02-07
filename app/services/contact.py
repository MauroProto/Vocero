import logging
import re
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Matches international phone numbers: +54 9 11 2233-4455, +1 (234) 567-8901, +442071234567, etc.
_PHONE_RE = re.compile(
    r"\+?\d[\d\s\-().]{6,}\d"
)


@dataclass
class ParsedContact:
    name: str | None
    phone: str


def _normalize_phone(raw: str) -> str:
    """Strip everything except digits and leading +."""
    digits = re.sub(r"[^\d+]", "", raw)
    if not digits.startswith("+"):
        digits = "+" + digits
    return digits


def parse_vcard(vcard_text: str) -> ParsedContact | None:
    """Extract name and phone from a vCard string."""
    name = None
    phone = None

    for line in vcard_text.splitlines():
        line = line.strip()
        if line.upper().startswith("FN:"):
            name = line.split(":", 1)[1].strip()
        elif line.upper().startswith("TEL") and ":" in line:
            phone = line.split(":", 1)[1].strip()

    if not phone:
        return None

    return ParsedContact(name=name, phone=_normalize_phone(phone))


async def download_and_parse_vcard(media_url: str) -> ParsedContact | None:
    """Download vCard from Twilio media URL and parse it."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            media_url,
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
        )
        if resp.status_code != 200:
            logger.error("Failed to download vCard: %s", resp.status_code)
            return None
        vcard_text = resp.text

    logger.info("Downloaded vCard: %s", vcard_text[:200])
    return parse_vcard(vcard_text)


def extract_phone_from_text(text: str) -> str | None:
    """Extract the first phone number found in a text message."""
    match = _PHONE_RE.search(text)
    if not match:
        return None
    return _normalize_phone(match.group())
