import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum

from app.schemas.intent import Entities, IntentType, Language

logger = logging.getLogger(__name__)


class ConversationStatus(StrEnum):
    IDLE = "idle"
    AWAITING_PROVIDER = "awaiting_provider"
    CALLING = "calling"
    AWAITING_USER_DECISION = "awaiting_user_decision"
    COMPLETED = "completed"


@dataclass
class ConversationState:
    status: ConversationStatus = ConversationStatus.IDLE
    pending_intent: IntentType | None = None
    pending_entities: Entities | None = None
    language: Language = Language.ES
    provider_phone: str | None = None
    provider_name: str | None = None
    active_call_ids: list[str] = field(default_factory=list)
    call_results: list[dict] = field(default_factory=list)
    last_bot_message: str | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# Module-level store keyed by WhatsApp number
_conversations: dict[str, ConversationState] = {}


def get_state(phone: str) -> ConversationState:
    """Return existing conversation state or create a new idle one."""
    if phone not in _conversations:
        _conversations[phone] = ConversationState()
    return _conversations[phone]


def reset_state(phone: str) -> None:
    """Reset conversation to idle, clearing all fields."""
    _conversations[phone] = ConversationState()


def merge_entities(existing: Entities | None, new: Entities) -> Entities:
    """Merge new entities into existing ones. New non-None values override."""
    if existing is None:
        return new.model_copy()

    merged_data = existing.model_dump()
    for key, value in new.model_dump(exclude_none=True).items():
        merged_data[key] = value
    return Entities(**merged_data)


def build_context(state: ConversationState) -> str | None:
    """Build a context string for the intent parser from current state.

    Returns None if idle with no relevant history.
    """
    if state.status == ConversationStatus.IDLE and not state.last_bot_message:
        return None

    parts: list[str] = []
    parts.append(f"State: {state.status}.")

    if state.pending_entities:
        entity_info = state.pending_entities.model_dump(exclude_none=True)
        if entity_info:
            details = ", ".join(f"{k}: {v}" for k, v in entity_info.items())
            parts.append(f"User needs: {details}.")

    if state.provider_phone:
        name = state.provider_name or "unknown"
        parts.append(f"Provider: {name} ({state.provider_phone}).")

    if state.last_bot_message:
        parts.append(f'Last bot message: "{state.last_bot_message}"')

    return " ".join(parts)
