"""Google Calendar link generator for Vocero."""

import logging
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)


async def build_calendar_link(
    summary: str,
    start_date: str,
    start_time: str,
    duration_minutes: int = 60,
    location: str | None = None,
    description: str | None = None,
) -> str:
    """Build a short Google Calendar 'Add Event' link.

    User taps the link in WhatsApp → Google Calendar opens with event pre-filled → taps Save.
    """
    start = start_date.replace("-", "") + "T" + start_time.replace(":", "") + "00"

    start_minutes = int(start_time.split(":")[0]) * 60 + int(start_time.split(":")[1])
    end_minutes = start_minutes + duration_minutes
    end_h, end_m = divmod(end_minutes, 60)
    end = start_date.replace("-", "") + f"T{end_h:02d}{end_m:02d}00"

    params = [
        "action=TEMPLATE",
        f"text={quote(summary)}",
        f"dates={start}/{end}",
        "ctz=America/Argentina/Buenos_Aires",
    ]
    if location:
        params.append(f"location={quote(location)}")

    long_url = "https://calendar.google.com/calendar/render?" + "&".join(params)

    short = await _shorten_url(long_url)
    return short or long_url


async def _shorten_url(url: str) -> str | None:
    """Shorten a URL via TinyURL. Returns short URL or None on failure."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "https://tinyurl.com/api-create.php",
                params={"url": url},
            )
            if resp.status_code == 200 and resp.text.startswith("https://"):
                return resp.text.strip()
    except Exception:
        logger.warning("URL shortener failed, using long URL")
    return None
