from enum import StrEnum

from pydantic import BaseModel, Field


class IntentType(StrEnum):
    CALL_NUMBER = "call_number"
    REQUEST_APPOINTMENT = "request_appointment"
    CONFIRM = "confirm"
    CANCEL = "cancel"
    HELP = "help"


class Language(StrEnum):
    EN = "en"
    ES = "es"


class Entities(BaseModel):
    phone_number: str | None = None
    provider_name: str | None = None
    service_type: str | None = None
    date_preference: str | None = None
    time_preference: str | None = None
    location: str | None = None
    special_requests: str | None = None


class IntentResult(BaseModel):
    intent: IntentType
    entities: Entities = Field(default_factory=Entities)
    language: Language = Language.EN
    confidence: float = Field(ge=0.0, le=1.0)
    response_message: str
