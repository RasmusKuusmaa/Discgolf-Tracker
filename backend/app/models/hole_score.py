import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampedUUIDMixin

if TYPE_CHECKING:
    from app.models.hole import Hole
    from app.models.round_player import RoundPlayer


class HoleScore(TimestampedUUIDMixin, Base):
    __tablename__ = "hole_scores"
    __table_args__ = (
        UniqueConstraint("round_player_id", "hole_id", name="uq_hole_scores_player_hole"),
    )

    round_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rounds.id"), nullable=False, index=True
    )
    round_player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("round_players.id"), nullable=False, index=True
    )
    hole_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("holes.id"), nullable=False, index=True
    )
    strokes: Mapped[int] = mapped_column(Integer, nullable=False)
    penalty_strokes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_circle_hit: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_fairway_hit: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    round_player: Mapped["RoundPlayer"] = relationship(back_populates="hole_scores")
    hole: Mapped["Hole"] = relationship()
