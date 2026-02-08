"""Formatted WhatsApp message templates for Vocero."""


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
    import re
    return re.sub(r"</?[A-Za-z]+>", "", text).strip()


def format_call_summary(
    provider_name: str | None,
    conversation_data: dict,
    language: str = "es",
) -> str:
    """Format a short post-call summary (no transcript)."""
    name = provider_name or "the provider"
    analysis = conversation_data.get("analysis") or {}
    summary_text = analysis.get("transcript_summary", "")

    if language == "es":
        lines = [f"Llamada con *{name}* finalizada."]
        if summary_text:
            lines.append(f"\n{summary_text}")
        lines.append("\nPedime *\"transcript\"* si queres ver la conversacion completa.")
    else:
        lines = [f"Call with *{name}* finished."]
        if summary_text:
            lines.append(f"\n{summary_text}")
        lines.append("\nSend *\"transcript\"* if you want the full conversation.")

    return "\n".join(lines)


def format_transcript(
    provider_name: str | None,
    conversation_data: dict,
) -> str:
    """Format the full call transcript."""
    name = provider_name or "the provider"
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
