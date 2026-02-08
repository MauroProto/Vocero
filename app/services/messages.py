"""Formatted WhatsApp message templates for Vocero."""

import logging
import re

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None

_SUMMARY_PROMPT = """\
You are analyzing a phone call transcript between a voice assistant ("agent") and a service provider ("user").

Your job: write a SHORT, natural summary of what happened in the call. This summary will be sent via WhatsApp to the person who requested the call.

Rules:
- Write in {language_name} ({language_code}).
- If an appointment/booking was confirmed: include the date, time, and any important details (address, what to bring, cost, etc.).
- If no appointment was booked: explain why (no availability, wrong number, voicemail, etc.).
- If something else happened (information gathered, message left, etc.): summarize the key takeaway.
- Be concise: 2-4 sentences max. This is WhatsApp, not an email.
- Use a casual, friendly tone. In Spanish use "vos" (Argentine style).
- Use WhatsApp formatting: *bold* for important details like dates/times.
- Do NOT start with "La llamada..." or "The call..." — go straight to the result.
- Do NOT include greetings or sign-offs.
"""


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url="https://api.openai.com/v1",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            timeout=15.0,
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
) -> str:
    """Use OpenAI to analyze the full transcript and generate an intelligent summary."""
    name = provider_name or provider_phone or "?"
    transcript_text = _build_transcript_text(conversation_data, name)

    if not transcript_text:
        if language == "es":
            return f"Llamada con *{name}* finalizada. No pude obtener detalles de la conversacion."
        return f"Call with *{name}* finished. Couldn't get conversation details."

    language_name = "Spanish" if language == "es" else "English"
    system_prompt = _SUMMARY_PROMPT.format(language_name=language_name, language_code=language)

    user_content = f"Provider called: {name}\n\nFull transcript:\n{transcript_text}"

    client = _get_client()
    try:
        resp = await client.post(
            "/chat/completions",
            json={
                "model": "gpt-5.2",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "max_tokens": 300,
                "temperature": 0.3,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        summary = data["choices"][0]["message"]["content"].strip()

        if language == "es":
            lines = [
                f"Llamada con *{name}* finalizada.\n",
                summary,
                "\nPedime *\"transcript\"* si queres ver la conversacion completa.",
            ]
        else:
            lines = [
                f"Call with *{name}* finished.\n",
                summary,
                "\nSend *\"transcript\"* if you want the full conversation.",
            ]
        return "\n".join(lines)

    except Exception:
        logger.exception("Failed to generate smart summary, falling back to basic")
        return _format_basic_summary(name, conversation_data, language)


def _format_basic_summary(name: str, conversation_data: dict, language: str) -> str:
    """Fallback summary when LLM is unavailable."""
    detail = _extract_last_substantive_message(conversation_data)
    if language == "es":
        lines = [f"Llamada con *{name}* finalizada."]
        if detail:
            lines.append(f"\n{detail}")
        lines.append("\nPedime *\"transcript\"* si queres ver la conversacion completa.")
    else:
        lines = [f"Call with *{name}* finished."]
        if detail:
            lines.append(f"\n{detail}")
        lines.append("\nSend *\"transcript\"* if you want the full conversation.")
    return "\n".join(lines)


def _extract_last_substantive_message(conversation_data: dict) -> str:
    """Get the last substantive agent message as a basic fallback."""
    transcript = conversation_data.get("transcript", [])
    for entry in reversed(transcript):
        msg = entry.get("message") or ""
        msg = _clean_agent_text(msg)
        if entry.get("role") == "agent" and len(msg) > 30:
            return msg
    return ""


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
        lines.append("\nResponde con el *numero* para llamar.")
    else:
        lines.append("\nReply with the *number* to call.")

    return "\n\n".join(lines)
