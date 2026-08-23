import math

from geoalchemy2.elements import WKTElement

from app.schemas.geo import Coordinates

_EARTH_RADIUS_M = 6_371_000


def to_point(coordinates: Coordinates) -> WKTElement:
    return WKTElement(f"POINT({coordinates.lng} {coordinates.lat})", srid=4326)


def haversine_distance_m(a: Coordinates, b: Coordinates) -> float:
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlat = lat2 - lat1
    dlng = math.radians(b.lng - a.lng)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(h))
