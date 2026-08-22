import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.geo import Coordinates, coordinates_from_geography


class HoleCreate(BaseModel):
    id: uuid.UUID
    number: int = Field(ge=1)
    par: int = Field(ge=1, le=10)
    distance_m: float | None = None
    tee_location: Coordinates | None = None
    basket_location: Coordinates | None = None
    elevation_delta_m: float | None = None
    notes: str | None = None


class HoleUpdate(BaseModel):
    par: int | None = Field(default=None, ge=1, le=10)
    distance_m: float | None = None
    tee_location: Coordinates | None = None
    basket_location: Coordinates | None = None
    elevation_delta_m: float | None = None
    notes: str | None = None


class HoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    number: int
    par: int
    distance_m: float | None
    tee_location: Coordinates | None
    basket_location: Coordinates | None
    elevation_delta_m: float | None
    notes: str | None

    @field_validator("tee_location", "basket_location", mode="before")
    @classmethod
    def _convert_locations(cls, value: Any) -> Any:
        return coordinates_from_geography(value)
