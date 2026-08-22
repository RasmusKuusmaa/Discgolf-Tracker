import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.hole import HoleCreate, HoleRead


class LayoutCreate(BaseModel):
    id: uuid.UUID
    name: str = Field(min_length=1, max_length=80)
    difficulty: str | None = None
    is_default: bool = False
    holes: list[HoleCreate] = Field(min_length=1)


class LayoutUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    difficulty: str | None = None
    is_default: bool | None = None
    is_active: bool | None = None


class LayoutRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    hole_count: int
    par_total: int
    total_distance_m: float | None
    difficulty: str | None
    is_default: bool
    is_active: bool
    holes: list[HoleRead] = []
