import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CourseFlagCreate(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class CourseFlagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    reported_by_id: uuid.UUID
    reason: str
    created_at: datetime


class CourseFlagListResponse(BaseModel):
    items: list[CourseFlagRead]
