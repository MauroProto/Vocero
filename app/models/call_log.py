import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CallLog(Base):
    __tablename__ = "call_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    appointment_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("appointment_requests.id")
    )
    provider_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_phone: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="initiated")
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    appointment_request: Mapped["AppointmentRequest"] = relationship(
        back_populates="call_logs"
    )
    appointment: Mapped["Appointment | None"] = relationship(
        back_populates="call_log", lazy="selectin"
    )
