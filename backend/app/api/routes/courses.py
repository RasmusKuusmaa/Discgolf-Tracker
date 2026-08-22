import base64
import uuid

from fastapi import APIRouter, Depends, Query, status
from geoalchemy2.elements import WKTElement
from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_current_user_optional
from app.core.errors import AppError
from app.core.slugs import slugify
from app.db.session import get_session
from app.models.course import Course
from app.models.hole import Hole
from app.models.layout import Layout
from app.models.user import User
from app.schemas.course import CourseCreate, CourseListResponse, CourseRead
from app.schemas.geo import Coordinates

router = APIRouter(prefix="/courses", tags=["courses"])


def _course_with_layouts_stmt() -> Select[tuple[Course]]:
    return select(Course).options(selectinload(Course.layouts).selectinload(Layout.holes))


def _point(coordinates: Coordinates) -> WKTElement:
    return WKTElement(f"POINT({coordinates.lng} {coordinates.lat})", srid=4326)


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
        location=_point(payload.location),
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
                    tee_location=_point(hole_in.tee_location) if hole_in.tee_location else None,
                    basket_location=(
                        _point(hole_in.basket_location) if hole_in.basket_location else None
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
            Course.id.in_(select(Layout.course_id).where(Layout.hole_count >= min_holes))
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
