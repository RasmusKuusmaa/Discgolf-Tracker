import uuid

from geoalchemy2 import Geography
from sqlalchemy import ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampedUUIDMixin


class Hole(TimestampedUUIDMixin, Base):
    __tablename__ = "holes"
    __table_args__ = (UniqueConstraint("layout_id", "number", name="uq_holes_layout_number"),)

    layout_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("layouts.id"), nullable=False, index=True
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    par: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_m: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    tee_location: Mapped[str | None] = mapped_column(
        Geography(geometry_type="POINT", srid=4326), nullable=True
    )
    basket_location: Mapped[str | None] = mapped_column(
        Geography(geometry_type="POINT", srid=4326), nullable=True
    )
    elevation_delta_m: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
