from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_user_optional
from app.core.errors import AppError
from app.core.friendships import is_blocked_pair
from app.db.session import get_session
from app.models.friendship import Friendship, FriendshipStatus
from app.models.user import User, Visibility
from app.schemas.user import UserPublicRead, UserRead, UserSearchResponse, UserUpdate

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


@router.get("/search", response_model=UserSearchResponse)
async def search_users(
    q: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    viewer: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserSearchResponse:
    pattern = f"%{q}%"
    blocked_subquery = select(Friendship.id).where(
        Friendship.deleted_at.is_(None),
        Friendship.status == FriendshipStatus.BLOCKED,
        or_(
            and_(Friendship.requester_id == viewer.id, Friendship.addressee_id == User.id),
            and_(Friendship.requester_id == User.id, Friendship.addressee_id == viewer.id),
        ),
    )

    stmt = (
        select(User)
        .where(
            User.id != viewer.id,
            User.allow_friend_requests.is_(True),
            or_(User.username.ilike(pattern), User.display_name.ilike(pattern)),
            ~blocked_subquery.exists(),
        )
        .order_by(User.username)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return UserSearchResponse(items=list(result.scalars()))


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
