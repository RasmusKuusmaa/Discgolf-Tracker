import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.course import CourseStatus, CourseVisibility
from app.schemas.geo import Coordinates, coordinates_from_geography
from app.schemas.layout import LayoutCreate, LayoutRead


class CourseCreate(BaseModel):
    id: uuid.UUID
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    city: str | None = None
    region: str | None = None
    country: str | None = Field(default=None, min_length=2, max_length=2)
    location: Coordinates
    visibility: CourseVisibility = CourseVisibility.PUBLIC
    layouts: list[LayoutCreate] = Field(min_length=1)


class CourseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    city: str | None = None
    region: str | None = None
    country: str | None = Field(default=None, min_length=2, max_length=2)
    visibility: CourseVisibility | None = None


class CourseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    city: str | None
    region: str | None
    country: str | None
    location: Coordinates
    created_by_id: uuid.UUID
    visibility: CourseVisibility
    status: CourseStatus
    is_verified: bool
    created_at: datetime
    layouts: list[LayoutRead] = []

    @field_validator("location", mode="before")
    @classmethod
    def _convert_location(cls, value: Any) -> Any:
        return coordinates_from_geography(value)


class CourseSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    city: str | None
    region: str | None
    country: str | None
    location: Coordinates
    visibility: CourseVisibility
    status: CourseStatus
    created_at: datetime

    @field_validator("location", mode="before")
    @classmethod
    def _convert_location(cls, value: Any) -> Any:
        return coordinates_from_geography(value)


class CourseListResponse(BaseModel):
    items: list[CourseSummary]
    next_cursor: str | None = None
