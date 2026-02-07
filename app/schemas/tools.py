"""Pydantic schemas for ElevenLabs voice agent server tool webhooks."""

from pydantic import BaseModel, Field


class SlotInfo(BaseModel):
    date: str
    time: str
    notes: str | None = None


class ReportSlotsRequest(BaseModel):
    conversation_id: str
    slots: list[SlotInfo] = Field(default_factory=list)
    provider_name: str | None = None


class CheckPreferenceRequest(BaseModel):
    conversation_id: str
    proposed_date: str
    proposed_time: str


class CheckPreferenceResponse(BaseModel):
    accept: bool
    reason: str


class ConfirmBookingRequest(BaseModel):
    conversation_id: str
    provider_name: str | None = None
    date: str
    time: str
    notes: str | None = None


class EndCallRequest(BaseModel):
    conversation_id: str
    reason: str = "no_availability"
