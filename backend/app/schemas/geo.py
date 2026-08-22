from typing import Any

from geoalchemy2.shape import to_shape
from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


def coordinates_from_geography(value: Any) -> Any:
    """Adapts a geoalchemy2 WKBElement to Coordinates for a pydantic
    `mode="before"` field validator; passes through None/dict/Coordinates."""
    if value is None or isinstance(value, Coordinates | dict):
        return value
    point = to_shape(value)
    return Coordinates(lat=point.y, lng=point.x)
