from app.core.geo import haversine_distance_m, to_point
from app.models.hole import Hole
from app.schemas.hole import HoleCreate


def build_hole(hole_in: HoleCreate) -> Hole:
    distance_m = hole_in.distance_m
    if distance_m is None and hole_in.tee_location and hole_in.basket_location:
        distance_m = haversine_distance_m(hole_in.tee_location, hole_in.basket_location)

    return Hole(
        id=hole_in.id,
        number=hole_in.number,
        par=hole_in.par,
        distance_m=distance_m,
        tee_location=to_point(hole_in.tee_location) if hole_in.tee_location else None,
        basket_location=to_point(hole_in.basket_location) if hole_in.basket_location else None,
        elevation_delta_m=hole_in.elevation_delta_m,
        notes=hole_in.notes,
    )
