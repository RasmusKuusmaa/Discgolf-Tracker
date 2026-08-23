"""Seed courses from OpenStreetMap via the Overpass API.

Course data pulled by this script is (c) OpenStreetMap contributors and is
licensed under the Open Database License (ODbL) -
https://www.openstreetmap.org/copyright. Any use of this data must carry
that attribution.

Usage:
    uv run python scripts/seed_osm.py \\
        --min-lat 59.3 --min-lng 24.5 --max-lat 59.5 --max-lng 24.9 \\
        --created-by <existing-user-uuid>
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.geo import to_point  # noqa: E402
from app.core.slugs import slugify  # noqa: E402
from app.db.session import async_session_maker  # noqa: E402
from app.models.course import Course, CourseStatus, CourseVisibility  # noqa: E402
from app.models.layout import Layout  # noqa: E402
from app.schemas.geo import Coordinates  # noqa: E402

ODBL_ATTRIBUTION = (
    "Course data (c) OpenStreetMap contributors, licensed under the "
    "Open Database License (ODbL) - https://www.openstreetmap.org/copyright"
)

DEFAULT_OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def build_query(min_lat: float, min_lng: float, max_lat: float, max_lng: float) -> str:
    bbox = f"{min_lat},{min_lng},{max_lat},{max_lng}"
    return f"""
    [out:json][timeout:60];
    (
      node["leisure"="disc_golf_course"]({bbox});
      way["leisure"="disc_golf_course"]({bbox});
      node["sport"="disc_golf"]({bbox});
      way["sport"="disc_golf"]({bbox});
    );
    out center tags;
    """


async def fetch_osm_elements(
    overpass_url: str, min_lat: float, min_lng: float, max_lat: float, max_lng: float
) -> list[dict[str, Any]]:
    query = build_query(min_lat, min_lng, max_lat, max_lng)
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(overpass_url, data={"data": query})
        response.raise_for_status()
        elements: list[dict[str, Any]] = response.json()["elements"]
        return elements


def element_coordinates(element: dict[str, Any]) -> tuple[float, float] | None:
    if "lat" in element and "lon" in element:
        return element["lat"], element["lon"]
    center = element.get("center")
    if center:
        return center["lat"], center["lon"]
    return None


async def unique_slug(session: AsyncSession, name: str, course_id: uuid.UUID) -> str:
    base = slugify(name)
    existing = await session.execute(select(Course.id).where(Course.slug == base))
    if existing.scalar_one_or_none() is None:
        return base
    return f"{base}-{str(course_id)[:8]}"


async def upsert_course(
    session: AsyncSession, element: dict[str, Any], created_by_id: uuid.UUID
) -> str:
    coords = element_coordinates(element)
    if coords is None:
        return "skipped"
    lat, lng = coords

    tags = element.get("tags", {})
    name = tags.get("name") or "Unnamed Disc Golf Course"
    osm_id = f"{element['type']}/{element['id']}"

    result = await session.execute(select(Course).where(Course.osm_id == osm_id))
    course = result.scalar_one_or_none()

    point = to_point(Coordinates(lat=lat, lng=lng))

    if course is not None:
        course.name = name
        course.location = point  # type: ignore[assignment]
        course.is_verified = True
        return "updated"

    course_id = uuid.uuid4()
    course = Course(
        id=course_id,
        name=name,
        slug=await unique_slug(session, name, course_id),
        city=tags.get("addr:city"),
        country=(tags.get("addr:country") or "")[:2] or None,
        location=point,
        created_by_id=created_by_id,
        visibility=CourseVisibility.PUBLIC,
        osm_id=osm_id,
        is_verified=True,
    )
    course.status = CourseStatus.PUBLISHED
    course.layouts.append(Layout(id=uuid.uuid4(), name="Main"))
    session.add(course)
    return "created"


async def seed(
    overpass_url: str,
    min_lat: float,
    min_lng: float,
    max_lat: float,
    max_lng: float,
    created_by: uuid.UUID,
) -> None:
    print(ODBL_ATTRIBUTION)

    elements = await fetch_osm_elements(overpass_url, min_lat, min_lng, max_lat, max_lng)
    print(f"Fetched {len(elements)} candidate elements from Overpass")

    counts = {"created": 0, "updated": 0, "skipped": 0}
    async with async_session_maker() as session:
        for element in elements:
            outcome = await upsert_course(session, element, created_by)
            counts[outcome] += 1
        await session.commit()

    print(f"Done: {counts['created']} created, {counts['updated']} updated, "
          f"{counts['skipped']} skipped")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-lat", type=float, required=True)
    parser.add_argument("--min-lng", type=float, required=True)
    parser.add_argument("--max-lat", type=float, required=True)
    parser.add_argument("--max-lng", type=float, required=True)
    parser.add_argument(
        "--created-by",
        type=uuid.UUID,
        required=True,
        help="UUID of an existing user to attribute imported courses to",
    )
    parser.add_argument("--overpass-url", default=DEFAULT_OVERPASS_URL)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(
        seed(
            args.overpass_url,
            args.min_lat,
            args.min_lng,
            args.max_lat,
            args.max_lng,
            args.created_by,
        )
    )


if __name__ == "__main__":
    main()
