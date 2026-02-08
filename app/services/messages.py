"""Formatted WhatsApp message templates for Vocero."""

import json
import logging
import re
from dataclasses import dataclass
from datetime import date

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None

_SUMMARY_PROMPT = """\
You are analyzing a phone call transcript between a voice assistant ("agent") and a service provider ("user").

Your job: extract structured data about what happened in the call AND write a SHORT summary for WhatsApp.

Rules for summary_text:
- Write in {language_name} ({language_code}).
- If an appointment/booking was confirmed: include the date, time, and any important details.
- If no appointment was booked: explain why (no availability, wrong number, voicemail, etc.).
- Be concise: 2-4 sentences max. This is WhatsApp, not an email.
- Use a casual, friendly tone. In Spanish use "vos" (Argentine style).
- Use WhatsApp formatting: *bold* for important details like dates/times.
- Do NOT start with "La llamada..." or "The call..." — go straight to the result.
- Do NOT include greetings or sign-offs.

Rules for booking fields:
- Set booking_confirmed to true ONLY if a specific appointment was agreed upon with a date and time.
- date format: YYYY-MM-DD. time format: HH:MM (24h).
- If no booking was confirmed, set booking_confirmed to false and leave other booking fields null.
- duration_minutes: estimate based on the service type if not explicitly stated (default 60).
- service_description: short label of what was booked, e.g. "Corte de pelo con Juan", "Consulta médica", "Revisión del auto". Do NOT include date/time here.
- notes: any extra useful info for the user (cost, what to bring, instructions). Keep it factual and short. Do NOT include internal reasoning or analysis.
"""

_SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "summary_text": {"type": "string", "description": "WhatsApp summary message"},
        "booking_confirmed": {"type": "boolean"},
        "date": {"anyOf": [{"type": "string"}, {"type": "null"}], "description": "YYYY-MM-DD or null"},
        "time": {"anyOf": [{"type": "string"}, {"type": "null"}], "description": "HH:MM 24h or null"},
        "duration_minutes": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
        "provider_name": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "address": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "service_description": {"anyOf": [{"type": "string"}, {"type": "null"}], "description": "Short label: Corte de pelo con Juan"},
        "notes": {"anyOf": [{"type": "string"}, {"type": "null"}], "description": "Extra info: cost, what to bring, etc."},
    },
    "required": ["summary_text", "booking_confirmed", "date", "time", "duration_minutes", "provider_name", "address", "service_description", "notes"],
    "additionalProperties": False,
}


@dataclass
class SmartSummaryResult:
    """Structured result from call transcript analysis."""
    summary_text: str
    booking_confirmed: bool
    date: str | None = None
    time: str | None = None
    duration_minutes: int | None = None
    provider_name: str | None = None
    address: str | None = None
    service_description: str | None = None
    notes: str | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url="https://api.openai.com/v1",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )
    return _client


def _build_transcript_text(conversation_data: dict, provider_name: str) -> str:
    """Build a plain-text transcript for LLM analysis."""
    transcript = conversation_data.get("transcript", [])
    lines = []
    for entry in transcript:
        role = entry.get("role", "")
        message = entry.get("message") or ""
        message = _clean_agent_text(message)
        if not message:
            continue
        if role == "agent":
            lines.append(f"Vocero: {message}")
        elif role == "user":
            lines.append(f"{provider_name}: {message}")
    return "\n".join(lines)


async def generate_smart_summary(
    provider_name: str,
    provider_phone: str | None,
    conversation_data: dict,
    language: str = "es",
) -> SmartSummaryResult:
    """Use OpenAI to analyze the full transcript and return structured summary + booking data."""
    name = provider_name or provider_phone or "?"
    transcript_text = _build_transcript_text(conversation_data, name)

    if not transcript_text:
        fallback = (
            f"Llamada con *{name}* finalizada. No pude obtener detalles de la conversacion."
            if language == "es"
            else f"Call with *{name}* finished. Couldn't get conversation details."
        )
        return SmartSummaryResult(summary_text=fallback, booking_confirmed=False)

    language_name = "Spanish" if language == "es" else "English"
    system_prompt = _SUMMARY_PROMPT.format(language_name=language_name, language_code=language)

    today = date.today().isoformat()
    user_content = f"Today's date: {today}\nProvider called: {name}\n\nFull transcript:\n{transcript_text}"

    request_body = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "max_completion_tokens": 500,
        "temperature": 0.3,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "call_summary",
                "strict": True,
                "schema": _SUMMARY_SCHEMA,
            },
        },
    }

    # Try gpt-5.2 first, fall back to gpt-4.1-mini if it fails
    client = _get_client()
    raw = None
    for model in ("gpt-5.2", "gpt-4.1-mini"):
        try:
            request_body["model"] = model
            resp = await client.post("/chat/completions", json=request_body)
            resp.raise_for_status()
            data = resp.json()
            raw = json.loads(data["choices"][0]["message"]["content"])
            break
        except Exception:
            logger.exception("Summary failed with %s", model)

    if raw and raw.get("summary_text"):
        return SmartSummaryResult(
            summary_text=raw["summary_text"],
            booking_confirmed=raw.get("booking_confirmed", False),
            date=raw.get("date"),
            time=raw.get("time"),
            duration_minutes=raw.get("duration_minutes"),
            provider_name=raw.get("provider_name") or name,
            address=raw.get("address"),
            service_description=raw.get("service_description"),
            notes=raw.get("notes"),
        )

    # Last resort: clean message, never garbage
    if language == "es":
        fallback = "La llamada termino. Pedime *\"transcript\"* para ver que se hablo."
    else:
        fallback = "The call ended. Send *\"transcript\"* to see what was discussed."
    return SmartSummaryResult(summary_text=fallback, booking_confirmed=False)


def format_summary_message(result: SmartSummaryResult, provider_name: str, language: str = "es") -> str:
    """Build the final WhatsApp message from a SmartSummaryResult."""
    name = provider_name or "?"
    if language == "es":
        lines = [
            f"Llamada con *{name}* finalizada.\n",
            result.summary_text,
            "\nPedime *\"transcript\"* si queres ver la conversacion completa.",
        ]
    else:
        lines = [
            f"Call with *{name}* finished.\n",
            result.summary_text,
            "\nSend *\"transcript\"* if you want the full conversation.",
        ]
    return "\n".join(lines)





def format_calling_message(provider_name: str | None, phone: str, language: str = "es") -> str:
    name = provider_name or phone
    if language == "es":
        return f"Llamando a *{name}*... Te aviso cuando tenga novedades."
    return f"Calling *{name}*... I'll update you shortly."


def format_slots_available(provider_name: str | None, language: str = "es") -> str:
    name = provider_name or "The provider"
    if language == "es":
        return f"*{name}* tiene disponibilidad! Estoy negociando el mejor turno para vos."
    return f"*{name}* has availability! I'm negotiating the best slot for you."


def format_no_availability(provider_name: str | None, language: str = "es") -> str:
    name = provider_name or "The provider"
    if language == "es":
        return f"*{name}* no tiene turnos disponibles en este momento."
    return f"*{name}* has no available slots right now."


def format_booking_confirmed(
    provider_name: str | None,
    date_time: str,
    address: str | None = None,
    notes: str | None = None,
    language: str = "es",
) -> str:
    name = provider_name or "The provider"
    if language == "es":
        lines = [
            "Turno confirmado!",
            "",
            f"*{name}*",
            f"Fecha/hora: {date_time}",
        ]
        if address:
            lines.append(f"Direccion: {address}")
        if notes:
            lines.append(f"Notas: {notes}")
    else:
        lines = [
            "Booking confirmed!",
            "",
            f"*{name}*",
            f"Date/time: {date_time}",
        ]
        if address:
            lines.append(f"Address: {address}")
        if notes:
            lines.append(f"Notes: {notes}")
    return "\n".join(lines)


def format_call_failed(provider_name: str | None, language: str = "es") -> str:
    name = provider_name or "the provider"
    if language == "es":
        return f"No pude completar la llamada a *{name}*. Queres que intente de nuevo?"
    return f"Couldn't complete the call to *{name}*. Want me to try again?"


def _clean_agent_text(text: str) -> str:
    """Remove XML-like language tags from agent responses."""
    return re.sub(r"</?[A-Za-z]+>", "", text).strip()


def format_transcript(
    provider_name: str | None,
    conversation_data: dict,
) -> str:
    """Format the full call transcript."""
    name = provider_name or "?"
    transcript = conversation_data.get("transcript", [])

    lines = [f"*Transcript — {name}*\n"]
    for entry in transcript:
        role = entry.get("role", "")
        message = entry.get("message") or ""
        message = _clean_agent_text(message)
        if not message:
            continue
        if role == "agent":
            lines.append(f"*Vocero:* {message}")
        elif role == "user":
            lines.append(f"*{name}:* {message}")

    return "\n".join(lines) if len(lines) > 1 else f"No hay transcript disponible para la llamada con *{name}*."


def format_multi_call_start(count: int, language: str = "es") -> str:
    """Message when starting parallel calls."""
    if language == "es":
        return f"Llamando a *{count}* proveedores en paralelo... Te aviso cuando tenga resultados."
    return f"Calling *{count}* providers in parallel... I'll let you know when I have results."


def format_multi_call_update(provider_name: str, outcome: str, language: str = "es") -> str:
    """Brief WhatsApp update for a single provider during multi-call."""
    name = provider_name or "?"
    if outcome == "booked":
        if language == "es":
            return f"Turno con *{name}* asegurado!"
        return f"Appointment with *{name}* booked!"
    elif outcome == "has_slots":
        if language == "es":
            return f"*{name}* tiene disponibilidad!"
        return f"*{name}* has availability!"
    elif outcome == "no_availability":
        if language == "es":
            return f"*{name}* no tiene turnos."
        return f"*{name}* has no slots."
    else:  # failed, busy, no-answer
        if language == "es":
            return f"No pude comunicarme con *{name}*."
        return f"Couldn't reach *{name}*."


def format_ranked_results(ranked_results: list[dict], language: str = "es") -> str:
    """Format consolidated multi-call results as a ranked WhatsApp message."""
    n = len(ranked_results)
    if language == "es":
        lines = [f"*Resultados de {n} llamadas:*\n"]
    else:
        lines = [f"*Results from {n} calls:*\n"]

    for i, r in enumerate(ranked_results, 1):
        summary = r.get("summary")
        name = r.get("provider_name", "?")
        rating = r.get("rating")
        total_ratings = r.get("total_ratings", 0)

        # Status line
        if summary and summary.booking_confirmed:
            if language == "es":
                status = "Turno confirmado!"
            else:
                status = "Booking confirmed!"
        elif summary and (summary.date or summary.time):
            if language == "es":
                status = "Tiene disponibilidad"
            else:
                status = "Has availability"
        elif r.get("outcome") in ("failed", "busy", "no-answer"):
            if language == "es":
                status = "No se pudo comunicar"
            else:
                status = "Couldn't connect"
        else:
            if language == "es":
                status = "Sin disponibilidad"
            else:
                status = "No availability"

        parts = [f"*{i}. {name}* — {status}"]

        # Date/time if available
        if summary and summary.date and summary.time:
            if language == "es":
                parts.append(f"   Fecha: {summary.date} {summary.time}")
            else:
                parts.append(f"   Date: {summary.date} {summary.time}")

        # Summary text
        if summary and summary.summary_text:
            parts.append(f"   {summary.summary_text}")

        # Rating
        if rating:
            stars = round(rating, 1)
            review_text = f"({total_ratings} reviews)" if total_ratings else ""
            parts.append(f"   Rating: {stars} {review_text}")

        lines.append("\n".join(parts))

    return "\n\n".join(lines)


def format_search_results(results: list, language: str = "es") -> str:
    """Format Google Places search results as a numbered WhatsApp message."""
    if not results:
        if language == "es":
            return "No encontre resultados. Intenta con otra busqueda."
        return "No results found. Try a different search."

    if language == "es":
        lines = ["Encontre estos resultados:\n"]
    else:
        lines = ["Here are the results:\n"]

    for i, r in enumerate(results, 1):
        parts = [f"*{i}. {r.name}*"]
        if r.rating:
            stars = round(r.rating, 1)
            parts.append(f"  Rating: {stars} ({r.total_ratings} reviews)")
        if r.address:
            parts.append(f"  {r.address}")
        if r.phone:
            parts.append(f"  Tel: {r.phone}")
        lines.append("\n".join(parts))

    if language == "es":
        lines.append("\nResponde con el *numero* para llamar, o *\"todos\"* para llamar a todos.")
    else:
        lines.append("\nReply with the *number* to call, or *\"all\"* to call them all.")

    return "\n\n".join(lines)
