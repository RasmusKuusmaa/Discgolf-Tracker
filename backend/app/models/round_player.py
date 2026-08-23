import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampedUUIDMixin

if TYPE_CHECKING:
    from app.models.round import Round
    from app.models.user import User


class RoundPlayer(TimestampedUUIDMixin, Base):
    __tablename__ = "round_players"
    __table_args__ = (
        CheckConstraint(
            "(user_id IS NULL) != (guest_name IS NULL)",
            name="ck_round_players_exactly_one_of_user_or_guest",
        ),
    )

    round_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rounds.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    guest_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    is_scorekeeper: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    round: Mapped["Round"] = relationship(back_populates="players")
    user: Mapped[Optional["User"]] = relationship()
