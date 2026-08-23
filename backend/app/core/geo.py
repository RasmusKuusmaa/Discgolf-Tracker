from geoalchemy2.elements import WKTElement

from app.schemas.geo import Coordinates


def to_point(coordinates: Coordinates) -> WKTElement:
    return WKTElement(f"POINT({coordinates.lng} {coordinates.lat})", srid=4326)
