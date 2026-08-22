import enum
import uuid

from geoalchemy2 import Geography
from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampedUUIDMixin


class CourseVisibility(enum.StrEnum):
    PUBLIC = "public"
    UNLISTED = "unlisted"


class CourseStatus(enum.StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    FLAGGED = "flagged"


class Course(TimestampedUUIDMixin, Base):
    __tablename__ = "courses"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    city: Mapped[str | None] = mapped_column(String(80), nullable=True)
    region: Mapped[str | None] = mapped_column(String(80), nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    location: Mapped[str] = mapped_column(
        Geography(geometry_type="POINT", srid=4326), nullable=False
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    visibility: Mapped[CourseVisibility] = mapped_column(
        default=CourseVisibility.PUBLIC, nullable=False
    )
    status: Mapped[CourseStatus] = mapped_column(default=CourseStatus.DRAFT, nullable=False)
    osm_id: Mapped[str | None] = mapped_column(String, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
