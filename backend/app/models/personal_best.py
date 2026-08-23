import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampedUUIDMixin

if TYPE_CHECKING:
    from app.models.layout import Layout
    from app.models.round import Round
    from app.models.user import User


class PersonalBest(TimestampedUUIDMixin, Base):
    __tablename__ = "personal_bests"
    __table_args__ = (
        UniqueConstraint("user_id", "layout_id", name="uq_personal_bests_user_layout"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    layout_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("layouts.id"), nullable=False, index=True
    )
    best_score_to_par: Mapped[int] = mapped_column(Integer, nullable=False)
    round_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rounds.id"), nullable=False
    )
    achieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship()
    layout: Mapped["Layout"] = relationship()
    round: Mapped["Round"] = relationship()
