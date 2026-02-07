import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    call_log_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("call_logs.id"), unique=True
    )
    provider_name: Mapped[str] = mapped_column(String(255))
    appointment_time: Mapped[datetime | None] = mapped_column(nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    call_log: Mapped["CallLog"] = relationship(back_populates="appointment")
