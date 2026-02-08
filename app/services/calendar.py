"""Google Calendar integration via Service Account."""

import json
import logging
import time

import httpx
import jwt

from app.config import settings

logger = logging.getLogger(__name__)

_SCOPES = "https://www.googleapis.com/auth/calendar.events"
_TOKEN_URI = "https://oauth2.googleapis.com/token"
_CALENDAR_API = "https://www.googleapis.com/calendar/v3"

_cached_token: str | None = None
_token_expiry: float = 0

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=15.0)
    return _client


def _load_service_account() -> dict:
    """Load service account credentials from JSON file."""
    path = settings.google_service_account_file
    if not path:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_FILE not configured")
    with open(path) as f:
        return json.load(f)


async def _get_access_token() -> str:
    """Get a valid access token, refreshing if needed (cached for 50 min)."""
    global _cached_token, _token_expiry

    if _cached_token and time.time() < _token_expiry:
        return _cached_token

    creds = _load_service_account()
    now = int(time.time())

    payload = {
        "iss": creds["client_email"],
        "scope": _SCOPES,
        "aud": _TOKEN_URI,
        "iat": now,
        "exp": now + 3600,
    }

    signed_jwt = jwt.encode(payload, creds["private_key"], algorithm="RS256")

    client = _get_client()
    resp = await client.post(
        _TOKEN_URI,
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": signed_jwt,
        },
    )
    resp.raise_for_status()
    token_data = resp.json()

    _cached_token = token_data["access_token"]
    _token_expiry = time.time() + 3000  # cache ~50 min
    return _cached_token


async def create_calendar_event(
    summary: str,
    start_date: str,
    start_time: str,
    duration_minutes: int = 60,
    location: str | None = None,
    description: str | None = None,
    timezone: str = "America/Argentina/Buenos_Aires",
) -> str | None:
    """Create a Google Calendar event. Returns the event HTML link or None on failure."""
    token = await _get_access_token()
    calendar_id = settings.google_calendar_id

    start_dt = f"{start_date}T{start_time}:00"
    # Calculate end time
    start_minutes = int(start_time.split(":")[0]) * 60 + int(start_time.split(":")[1])
    end_minutes = start_minutes + duration_minutes
    end_h, end_m = divmod(end_minutes, 60)
    end_dt = f"{start_date}T{end_h:02d}:{end_m:02d}:00"

    event_body = {
        "summary": summary,
        "start": {"dateTime": start_dt, "timeZone": timezone},
        "end": {"dateTime": end_dt, "timeZone": timezone},
    }
    if location:
        event_body["location"] = location
    if description:
        event_body["description"] = description

    client = _get_client()
    resp = await client.post(
        f"{_CALENDAR_API}/calendars/{calendar_id}/events",
        json=event_body,
        headers={"Authorization": f"Bearer {token}"},
    )

    if resp.status_code >= 400:
        logger.error("Calendar API error %s: %s", resp.status_code, resp.text)
        return None

    data = resp.json()
    link = data.get("htmlLink")
    logger.info("Calendar event created: %s", link)
    return link
