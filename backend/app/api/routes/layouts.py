import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.errors import AppError
from app.core.hole_factory import build_hole
from app.db.session import get_session
from app.models.course import Course
from app.models.layout import Layout
from app.models.round import Round
from app.models.user import User
from app.schemas.layout import LayoutCreate, LayoutRead, LayoutUpdate

router = APIRouter(prefix="/courses/{course_id}/layouts", tags=["layouts"])


async def _get_owned_course(session: AsyncSession, course_id: uuid.UUID, user: User) -> Course:
    result = await session.execute(
        select(Course).where(Course.id == course_id, Course.deleted_at.is_(None))
    )
    course = result.scalar_one_or_none()
    if course is None:
        raise AppError("course_not_found", "Course not found", status.HTTP_404_NOT_FOUND)
    if course.created_by_id != user.id and not user.is_admin:
        raise AppError(
            "not_course_owner",
            "Only the creator or an admin can do this",
            status.HTTP_403_FORBIDDEN,
        )
    return course


async def _get_layout(
    session: AsyncSession, course_id: uuid.UUID, layout_id: uuid.UUID
) -> Layout:
    result = await session.execute(
        select(Layout)
        .options(selectinload(Layout.holes))
        .where(
            Layout.id == layout_id,
            Layout.course_id == course_id,
            Layout.deleted_at.is_(None),
        )
    )
    layout = result.scalar_one_or_none()
    if layout is None:
        raise AppError("layout_not_found", "Layout not found", status.HTTP_404_NOT_FOUND)
    return layout


async def _layout_has_rounds(session: AsyncSession, layout_id: uuid.UUID) -> bool:
    result = await session.execute(select(Round.id).where(Round.layout_id == layout_id).limit(1))
    return result.scalar_one_or_none() is not None


@router.post("", response_model=LayoutRead, status_code=status.HTTP_201_CREATED)
async def create_layout(
    course_id: uuid.UUID,
    payload: LayoutCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Layout:
    await _get_owned_course(session, course_id, user)

    layout = Layout(
        id=payload.id,
        course_id=course_id,
        name=payload.name,
        difficulty=payload.difficulty,
        is_default=payload.is_default,
    )
    for hole_in in payload.holes:
        layout.holes.append(build_hole(hole_in))
    layout.recompute_totals()

    session.add(layout)
    await session.commit()
    return layout


@router.patch("/{layout_id}", response_model=LayoutRead)
async def update_layout(
    course_id: uuid.UUID,
    layout_id: uuid.UUID,
    payload: LayoutUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Layout:
    await _get_owned_course(session, course_id, user)
    layout = await _get_layout(session, course_id, layout_id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(layout, field, value)

    await session.commit()
    return layout


@router.delete("/{layout_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_layout(
    course_id: uuid.UUID,
    layout_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    await _get_owned_course(session, course_id, user)
    layout = await _get_layout(session, course_id, layout_id)

    if await _layout_has_rounds(session, layout_id):
        raise AppError(
            "layout_has_rounds",
            "Cannot delete a layout with recorded rounds; deactivate it instead",
            status.HTTP_409_CONFLICT,
        )

    layout.deleted_at = datetime.now(UTC)
    await session.commit()
