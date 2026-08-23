from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_user_optional
from app.core.errors import AppError
from app.core.friendships import is_blocked_pair
from app.db.session import get_session
from app.models.user import User, Visibility
from app.schemas.user import UserPublicRead, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def get_me(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("/me", response_model=UserRead)
async def update_me(
    payload: UserUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> User:
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(user, field, value)

    await session.commit()
    await session.refresh(user)
    return user


@router.get("/{username}", response_model=UserPublicRead)
async def get_user_by_username(
    username: str,
    viewer: User | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> User:
    result = await session.execute(select(User).where(User.username == username))
    target = result.scalar_one_or_none()

    if target is None:
        raise AppError("user_not_found", "User not found", status.HTTP_404_NOT_FOUND)

    is_self = viewer is not None and viewer.id == target.id
    if target.profile_visibility != Visibility.PUBLIC and not is_self:
        raise AppError("user_not_found", "User not found", status.HTTP_404_NOT_FOUND)

    if viewer is not None and not is_self and await is_blocked_pair(session, viewer.id, target.id):
        raise AppError("user_not_found", "User not found", status.HTTP_404_NOT_FOUND)

    return target
