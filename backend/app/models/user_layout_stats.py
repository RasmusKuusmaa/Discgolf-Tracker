import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampedUUIDMixin

if TYPE_CHECKING:
    from app.models.layout import Layout
    from app.models.user import User


class UserLayoutStats(TimestampedUUIDMixin, Base):
    __tablename__ = "user_layout_stats"
    __table_args__ = (
        UniqueConstraint("user_id", "layout_id", name="uq_user_layout_stats_user_layout"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    layout_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("layouts.id"), nullable=False, index=True
    )
    rounds_played: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_score_to_par: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    best_score_to_par: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship()
    layout: Mapped["Layout"] = relationship()
