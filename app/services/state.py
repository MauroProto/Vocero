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
    COMPLETED = "completed"


@dataclass
class MultiCallProvider:
    name: str
    phone: str
    rating: float | None = None
    total_ratings: int = 0
    call_sid: str | None = None
    conversation_id: str | None = None


@dataclass
class MultiCallCampaign:
    providers: list[MultiCallProvider]
    pending_count: int = 0
    results: list[dict] = field(default_factory=list)


@dataclass
class ConversationState:
    status: ConversationStatus = ConversationStatus.IDLE
    pending_intent: IntentType | None = None
    pending_entities: Entities | None = None
    language: Language = Language.ES
    user_name: str | None = None
    provider_phone: str | None = None
    provider_name: str | None = None
    active_call_ids: list[str] = field(default_factory=list)
    call_results: list[dict] = field(default_factory=list)
    last_bot_message: str | None = None
    message_history: list[str] = field(default_factory=list)
    search_results: list | None = None
    user_latitude: float | None = None
    user_longitude: float | None = None
    last_conversation_id: str | None = None
    multi_call: MultiCallCampaign | None = None
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


def find_state_by_conversation_id(conversation_id: str) -> tuple[str, ConversationState] | None:
    """Find the user phone and state that owns a given ElevenLabs conversation_id."""
    for phone, state in _conversations.items():
        if conversation_id in state.active_call_ids:
            return phone, state
        # Also search multi-call campaign providers
        if state.multi_call:
            for provider in state.multi_call.providers:
                if conversation_id in (provider.call_sid, provider.conversation_id):
                    return phone, state
    return None


def merge_entities(existing: Entities | None, new: Entities) -> Entities:
    """Merge new entities into existing ones. New non-None values override."""
    if existing is None:
        return new.model_copy()

    merged_data = existing.model_dump()
    for key, value in new.model_dump(exclude_none=True).items():
        merged_data[key] = value
    return Entities(**merged_data)


def add_message(state: ConversationState, role: str, text: str) -> None:
    """Add a message to the conversation history. Keeps last 10."""
    state.message_history.append(f"{role}: {text}")
    if len(state.message_history) > 10:
        state.message_history = state.message_history[-10:]


def build_context(state: ConversationState) -> str | None:
    """Build a rich context string for the intent parser."""
    if state.status == ConversationStatus.IDLE and not state.message_history:
        return None

    parts: list[str] = []
    parts.append(f"Current state: {state.status}.")

    if state.provider_phone:
        name = state.provider_name or "unknown"
        parts.append(f"Contact on file: {name} ({state.provider_phone}).")

    if state.pending_entities:
        entity_info = state.pending_entities.model_dump(exclude_none=True)
        if entity_info:
            details = ", ".join(f"{k}: {v}" for k, v in entity_info.items())
            parts.append(f"Known info: {details}.")

    if state.call_results:
        last = state.call_results[-1]
        parts.append(f"Last call result: {last}.")

    if state.message_history:
        recent = "\n".join(state.message_history[-6:])
        parts.append(f"\nRecent conversation:\n{recent}")

    return " ".join(parts)
