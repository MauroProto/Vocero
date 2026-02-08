"""Google Calendar link generator for Vocero."""

from urllib.parse import quote


def build_calendar_link(
    summary: str,
    start_date: str,
    start_time: str,
    duration_minutes: int = 60,
    location: str | None = None,
    description: str | None = None,
) -> str:
    """Build a Google Calendar 'Add Event' link.

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
    if description:
        params.append(f"details={quote(description)}")

    return "https://calendar.google.com/calendar/render?" + "&".join(params)
