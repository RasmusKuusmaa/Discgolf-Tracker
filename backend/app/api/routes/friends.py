import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import AppError
from app.db.session import get_session
from app.models.friendship import Friendship, FriendshipStatus
from app.models.user import User
from app.schemas.friendship import FriendRequestCreate, FriendshipRead

router = APIRouter(prefix="/friends", tags=["friends"])


async def _resolve_target_user(session: AsyncSession, payload: FriendRequestCreate) -> User:
    if payload.user_id is not None:
        user = await session.get(User, payload.user_id)
    else:
        result = await session.execute(select(User).where(User.username == payload.username))
        user = result.scalar_one_or_none()

    if user is None:
        raise AppError("user_not_found", "User not found", status.HTTP_404_NOT_FOUND)
    return user


async def _find_pair_friendship(
    session: AsyncSession, user_a_id: uuid.UUID, user_b_id: uuid.UUID
) -> Friendship | None:
    result = await session.execute(
        select(Friendship).where(
            Friendship.deleted_at.is_(None),
            or_(
                and_(Friendship.requester_id == user_a_id, Friendship.addressee_id == user_b_id),
                and_(Friendship.requester_id == user_b_id, Friendship.addressee_id == user_a_id),
            ),
        )
    )
    return result.scalar_one_or_none()


@router.post("/requests", response_model=FriendshipRead, status_code=status.HTTP_201_CREATED)
async def send_friend_request(
    payload: FriendRequestCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Friendship:
    target = await _resolve_target_user(session, payload)

    if target.id == user.id:
        raise AppError(
            "cannot_friend_self",
            "Cannot send a friend request to yourself",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    if not target.allow_friend_requests:
        raise AppError(
            "not_accepting_requests",
            "This user is not accepting friend requests",
            status.HTTP_403_FORBIDDEN,
        )

    existing = await _find_pair_friendship(session, user.id, target.id)
    if existing is not None:
        if existing.status == FriendshipStatus.BLOCKED:
            raise AppError(
                "blocked", "Cannot send a friend request to this user", status.HTTP_403_FORBIDDEN
            )
        if existing.status == FriendshipStatus.ACCEPTED:
            raise AppError(
                "already_friends",
                "You are already friends with this user",
                status.HTTP_409_CONFLICT,
            )
        raise AppError(
            "request_already_pending",
            "A friend request already exists between these users",
            status.HTTP_409_CONFLICT,
        )

    friendship = Friendship(
        requester_id=user.id, addressee_id=target.id, status=FriendshipStatus.PENDING
    )
    session.add(friendship)
    await session.commit()
    return friendship


async def _get_incoming_request(
    session: AsyncSession, request_id: uuid.UUID, user: User
) -> Friendship:
    result = await session.execute(
        select(Friendship).where(Friendship.id == request_id, Friendship.deleted_at.is_(None))
    )
    friendship = result.scalar_one_or_none()
    if friendship is None:
        raise AppError("request_not_found", "Friend request not found", status.HTTP_404_NOT_FOUND)
    if friendship.addressee_id != user.id:
        raise AppError(
            "not_addressee",
            "Only the recipient can respond to this request",
            status.HTTP_403_FORBIDDEN,
        )
    if friendship.status != FriendshipStatus.PENDING:
        raise AppError(
            "request_not_pending", "This request is not pending", status.HTTP_409_CONFLICT
        )
    return friendship


@router.post("/requests/{request_id}/accept", response_model=FriendshipRead)
async def accept_friend_request(
    request_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Friendship:
    friendship = await _get_incoming_request(session, request_id, user)
    friendship.status = FriendshipStatus.ACCEPTED
    friendship.responded_at = datetime.now(UTC)
    await session.commit()
    return friendship


@router.post("/requests/{request_id}/decline", status_code=status.HTTP_204_NO_CONTENT)
async def decline_friend_request(
    request_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    friendship = await _get_incoming_request(session, request_id, user)
    friendship.responded_at = datetime.now(UTC)
    friendship.deleted_at = datetime.now(UTC)
    await session.commit()


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_friend(
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    friendship = await _find_pair_friendship(session, user.id, user_id)
    if friendship is None or friendship.status != FriendshipStatus.ACCEPTED:
        raise AppError(
            "friendship_not_found",
            "No accepted friendship with this user",
            status.HTTP_404_NOT_FOUND,
        )
    friendship.deleted_at = datetime.now(UTC)
    await session.commit()
