from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampedUUIDMixin

if TYPE_CHECKING:
    from app.models.user_achievement import UserAchievement


class Achievement(TimestampedUUIDMixin, Base):
    __tablename__ = "achievements"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    icon: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    tier: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    xp_reward: Mapped[int] = mapped_column(Integer, nullable=False)
    criteria: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)

    user_achievements: Mapped[list["UserAchievement"]] = relationship(
        back_populates="achievement"
    )
