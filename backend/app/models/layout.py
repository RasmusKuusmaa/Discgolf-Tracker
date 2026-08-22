import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampedUUIDMixin

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.hole import Hole


class Layout(TimestampedUUIDMixin, Base):
    __tablename__ = "layouts"

    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    hole_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    par_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_distance_m: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    course: Mapped["Course"] = relationship(back_populates="layouts")
    holes: Mapped[list["Hole"]] = relationship(
        back_populates="layout", cascade="all, delete-orphan", order_by="Hole.number"
    )
