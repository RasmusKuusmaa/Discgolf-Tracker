import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import AppError
from app.core.friendships import find_pair_friendship
from app.db.session import get_session
from app.models.friendship import Friendship, FriendshipStatus
from app.models.user import User
from app.schemas.friendship import (
    FriendListItem,
    FriendListResponse,
    FriendRequestCreate,
    FriendRequestItem,
    FriendRequestsResponse,
    FriendshipRead,
    FriendSummary,
)

router = APIRouter(prefix="/friends", tags=["friends"])


@router.get("", response_model=FriendListResponse)
async def list_friends(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> FriendListResponse:
    stmt = select(Friendship).where(
        Friendship.deleted_at.is_(None),
        Friendship.status == FriendshipStatus.ACCEPTED,
        or_(Friendship.requester_id == user.id, Friendship.addressee_id == user.id),
    )
    friendships = list((await session.execute(stmt)).scalars())

    other_ids = [
        f.addressee_id if f.requester_id == user.id else f.requester_id for f in friendships
    ]
    users_by_id = {
        u.id: u
        for u in (await session.execute(select(User).where(User.id.in_(other_ids)))).scalars()
    }

    items = [
        FriendListItem(
            user=FriendSummary.model_validate(users_by_id[other_id]),
            friends_since=friendship.responded_at or friendship.created_at,
        )
        for friendship, other_id in zip(friendships, other_ids, strict=True)
        if other_id in users_by_id
    ]
    return FriendListResponse(items=items)


@router.get("/requests", response_model=FriendRequestsResponse)
async def list_friend_requests(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> FriendRequestsResponse:
    incoming = list(
        (
            await session.execute(
                select(Friendship).where(
                    Friendship.deleted_at.is_(None),
                    Friendship.status == FriendshipStatus.PENDING,
                    Friendship.addressee_id == user.id,
                )
            )
        ).scalars()
    )
    outgoing = list(
        (
            await session.execute(
                select(Friendship).where(
                    Friendship.deleted_at.is_(None),
                    Friendship.status == FriendshipStatus.PENDING,
                    Friendship.requester_id == user.id,
                )
            )
        ).scalars()
    )

    other_ids = {f.requester_id for f in incoming} | {f.addressee_id for f in outgoing}
    users_by_id = {
        u.id: u
        for u in (await session.execute(select(User).where(User.id.in_(other_ids)))).scalars()
    }

    return FriendRequestsResponse(
        incoming=[
            FriendRequestItem(
                id=f.id,
                user=FriendSummary.model_validate(users_by_id[f.requester_id]),
                created_at=f.created_at,
            )
            for f in incoming
            if f.requester_id in users_by_id
        ],
        outgoing=[
            FriendRequestItem(
                id=f.id,
                user=FriendSummary.model_validate(users_by_id[f.addressee_id]),
                created_at=f.created_at,
            )
            for f in outgoing
            if f.addressee_id in users_by_id
        ],
    )


async def _resolve_target_user(session: AsyncSession, payload: FriendRequestCreate) -> User:
    if payload.user_id is not None:
        user = await session.get(User, payload.user_id)
    else:
        result = await session.execute(select(User).where(User.username == payload.username))
        user = result.scalar_one_or_none()

    if user is None:
        raise AppError("user_not_found", "User not found", status.HTTP_404_NOT_FOUND)
    return user


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

    existing = await find_pair_friendship(session, user.id, target.id)
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
    friendship = await find_pair_friendship(session, user.id, user_id)
    if friendship is None or friendship.status != FriendshipStatus.ACCEPTED:
        raise AppError(
            "friendship_not_found",
            "No accepted friendship with this user",
            status.HTTP_404_NOT_FOUND,
        )
    friendship.deleted_at = datetime.now(UTC)
    await session.commit()


@router.post("/block/{user_id}", response_model=FriendshipRead)
async def block_user(
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Friendship:
    if user_id == user.id:
        raise AppError(
            "cannot_block_self", "Cannot block yourself", status.HTTP_422_UNPROCESSABLE_CONTENT
        )

    target = await session.get(User, user_id)
    if target is None:
        raise AppError("user_not_found", "User not found", status.HTTP_404_NOT_FOUND)

    friendship = await find_pair_friendship(session, user.id, user_id)
    if friendship is None:
        friendship = Friendship(requester_id=user.id, addressee_id=user_id)
        session.add(friendship)

    friendship.status = FriendshipStatus.BLOCKED
    friendship.responded_at = datetime.now(UTC)
    await session.commit()
    return friendship


@router.post("/unblock/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unblock_user(
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    friendship = await find_pair_friendship(session, user.id, user_id)
    if (
        friendship is None
        or friendship.status != FriendshipStatus.BLOCKED
        or friendship.requester_id != user.id
    ):
        raise AppError(
            "block_not_found", "You have not blocked this user", status.HTTP_404_NOT_FOUND
        )

    friendship.deleted_at = datetime.now(UTC)
    await session.commit()
