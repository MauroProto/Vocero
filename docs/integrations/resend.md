# Resend Integration Guide

## Purpose

Send call transcripts to users via email after appointment calls complete.

## Setup

```python
import resend

resend.api_key = settings.resend_api_key
```

## Sending Transcript Email

```python
async def send_transcript_email(
    to_email: str,
    provider_name: str,
    transcript: list[dict],
    appointment_details: dict | None = None,
):
    html_body = build_transcript_html(provider_name, transcript, appointment_details)

    resend.Emails.send({
        "from": settings.resend_from_email,
        "to": [to_email],
        "subject": f"Vocero - Call Transcript: {provider_name}",
        "html": html_body,
    })
```

## Email Template Structure

- **Header:** Vocero branding + call summary
- **Appointment details** (if booked): provider, date/time, address
- **Full transcript:** Speaker-labeled conversation with timestamps
- **Footer:** "Booked via Vocero"

## Key Constraints
- Resend free tier: 100 emails/day, 1 sending domain
- Must verify sending domain in Resend dashboard
- For hackathon: use `onboarding@resend.dev` as sender (no domain verification needed)
