import base64
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, status
from geoalchemy2 import Geography
from sqlalchemy import Select, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_current_user_optional
from app.core.errors import AppError
from app.core.geo import to_point
from app.core.slugs import slugify
from app.db.session import get_session
from app.models.course import Course
from app.models.hole import Hole
from app.models.layout import Layout
from app.models.user import User
from app.schemas.course import (
    CourseBboxResponse,
    CourseCreate,
    CourseListResponse,
    CourseNearby,
    CourseNearbyResponse,
    CourseRead,
    CourseSummary,
    CourseUpdate,
)
from app.schemas.geo import Coordinates

router = APIRouter(prefix="/courses", tags=["courses"])


def _course_with_layouts_stmt() -> Select[tuple[Course]]:
    return select(Course).options(selectinload(Course.layouts).selectinload(Layout.holes))


async def _unique_slug(session: AsyncSession, name: str, course_id: uuid.UUID) -> str:
    base = slugify(name)
    existing = await session.execute(select(Course.id).where(Course.slug == base))
    if existing.scalar_one_or_none() is None:
        return base
    return f"{base}-{str(course_id)[:8]}"


def _encode_cursor(course_id: uuid.UUID) -> str:
    return base64.urlsafe_b64encode(str(course_id).encode()).decode()


def _decode_cursor(cursor: str) -> uuid.UUID:
    try:
        return uuid.UUID(base64.urlsafe_b64decode(cursor.encode()).decode())
    except (ValueError, UnicodeDecodeError) as exc:
        raise AppError(
            "invalid_cursor", "Invalid pagination cursor", status.HTTP_400_BAD_REQUEST
        ) from exc


@router.post("", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
async def create_course(
    payload: CourseCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Course:
    slug = await _unique_slug(session, payload.name, payload.id)

    course = Course(
        id=payload.id,
        name=payload.name,
        slug=slug,
        description=payload.description,
        city=payload.city,
        region=payload.region,
        country=payload.country,
        location=to_point(payload.location),
        created_by_id=user.id,
        visibility=payload.visibility,
    )

    for layout_in in payload.layouts:
        layout = Layout(
            id=layout_in.id,
            name=layout_in.name,
            difficulty=layout_in.difficulty,
            is_default=layout_in.is_default,
        )
        for hole_in in layout_in.holes:
            layout.holes.append(
                Hole(
                    id=hole_in.id,
                    number=hole_in.number,
                    par=hole_in.par,
                    distance_m=hole_in.distance_m,
                    tee_location=to_point(hole_in.tee_location) if hole_in.tee_location else None,
                    basket_location=(
                        to_point(hole_in.basket_location) if hole_in.basket_location else None
                    ),
                    elevation_delta_m=hole_in.elevation_delta_m,
                    notes=hole_in.notes,
                )
            )
        course.layouts.append(layout)

    session.add(course)
    await session.commit()

    return course


@router.get("", response_model=CourseListResponse)
async def list_courses(
    q: str | None = None,
    country: str | None = Query(default=None, min_length=2, max_length=2),
    min_holes: int | None = Query(default=None, ge=1),
    created_by_me: bool = False,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    viewer: User | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> CourseListResponse:
    if created_by_me and viewer is None:
        raise AppError(
            "not_authenticated", "Authentication required", status.HTTP_401_UNAUTHORIZED
        )

    stmt = select(Course).where(Course.deleted_at.is_(None))

    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(or_(Course.name.ilike(pattern), Course.city.ilike(pattern)))
    if country:
        stmt = stmt.where(Course.country == country.upper())
    if created_by_me and viewer is not None:
        stmt = stmt.where(Course.created_by_id == viewer.id)
    if min_holes is not None:
        stmt = stmt.where(
            Course.id.in_(
                select(Layout.course_id).where(
                    Layout.hole_count >= min_holes, Layout.deleted_at.is_(None)
                )
            )
        )
    if cursor:
        stmt = stmt.where(Course.id < _decode_cursor(cursor))

    stmt = stmt.order_by(Course.id.desc()).limit(limit + 1)

    result = await session.execute(stmt)
    courses = list(result.scalars())

    has_more = len(courses) > limit
    courses = courses[:limit]
    next_cursor = _encode_cursor(courses[-1].id) if has_more and courses else None

    return CourseListResponse(items=courses, next_cursor=next_cursor)


@router.get("/nearby", response_model=CourseNearbyResponse)
async def list_nearby_courses(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(..., gt=0, le=500),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> CourseNearbyResponse:
    origin = to_point(Coordinates(lat=lat, lng=lng))
    distance = Course.location.ST_Distance(origin).label("distance_m")

    stmt = (
        select(Course, distance)
        .where(Course.deleted_at.is_(None))
        .where(Course.location.ST_DWithin(origin, radius_km * 1000))
        .order_by(distance)
        .limit(limit)
    )

    result = await session.execute(stmt)
    items = [
        CourseNearby(**CourseSummary.model_validate(course).model_dump(), distance_m=distance_m)
        for course, distance_m in result.all()
    ]

    return CourseNearbyResponse(items=items)


@router.get("/bbox", response_model=CourseBboxResponse)
async def list_courses_in_bbox(
    min_lat: float = Query(..., ge=-90, le=90),
    min_lng: float = Query(..., ge=-180, le=180),
    max_lat: float = Query(..., ge=-90, le=90),
    max_lng: float = Query(..., ge=-180, le=180),
    limit: int = Query(default=200, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> CourseBboxResponse:
    if min_lat >= max_lat or min_lng >= max_lng:
        raise AppError(
            "invalid_bbox",
            "min_lat/min_lng must be less than max_lat/max_lng",
            status.HTTP_400_BAD_REQUEST,
        )

    envelope = cast(func.ST_MakeEnvelope(min_lng, min_lat, max_lng, max_lat, 4326), Geography)

    stmt = (
        select(Course)
        .where(Course.deleted_at.is_(None))
        .where(func.ST_Intersects(Course.location, envelope))
        .limit(limit)
    )

    result = await session.execute(stmt)
    return CourseBboxResponse(items=list(result.scalars()))


@router.get("/{course_id}", response_model=CourseRead)
async def get_course(
    course_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Course:
    result = await session.execute(
        _course_with_layouts_stmt().where(
            Course.id == course_id, Course.deleted_at.is_(None)
        )
    )
    course = result.scalar_one_or_none()
    if course is None:
        raise AppError("course_not_found", "Course not found", status.HTTP_404_NOT_FOUND)

    return course


def _require_owner_or_admin(course: Course, user: User) -> None:
    if course.created_by_id != user.id and not user.is_admin:
        raise AppError(
            "not_course_owner",
            "Only the creator or an admin can do this",
            status.HTTP_403_FORBIDDEN,
        )


@router.patch("/{course_id}", response_model=CourseRead)
async def update_course(
    course_id: uuid.UUID,
    payload: CourseUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Course:
    result = await session.execute(
        _course_with_layouts_stmt().where(Course.id == course_id, Course.deleted_at.is_(None))
    )
    course = result.scalar_one_or_none()
    if course is None:
        raise AppError("course_not_found", "Course not found", status.HTTP_404_NOT_FOUND)

    _require_owner_or_admin(course, user)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(course, field, value)

    await session.commit()
    return course


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    result = await session.execute(
        select(Course).where(Course.id == course_id, Course.deleted_at.is_(None))
    )
    course = result.scalar_one_or_none()
    if course is None:
        raise AppError("course_not_found", "Course not found", status.HTTP_404_NOT_FOUND)

    _require_owner_or_admin(course, user)

    course.deleted_at = datetime.now(UTC)
    await session.commit()
