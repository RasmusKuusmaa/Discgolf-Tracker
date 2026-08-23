import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampedUUIDMixin

if TYPE_CHECKING:
    from app.models.layout import Layout
    from app.models.round_player import RoundPlayer
    from app.models.user import User


class RoundStatus(enum.StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class Round(TimestampedUUIDMixin, Base):
    __tablename__ = "rounds"

    layout_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("layouts.id"), nullable=False, index=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[RoundStatus] = mapped_column(default=RoundStatus.IN_PROGRESS, nullable=False)
    is_practice: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    weather_note: Mapped[str | None] = mapped_column(String, nullable=True)
    client_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    layout: Mapped["Layout"] = relationship()
    created_by: Mapped["User"] = relationship()
    players: Mapped[list["RoundPlayer"]] = relationship(
        back_populates="round", cascade="all, delete-orphan", order_by="RoundPlayer.position"
    )
