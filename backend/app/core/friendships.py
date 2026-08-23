import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.friendship import Friendship, FriendshipStatus


async def find_pair_friendship(
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


async def is_blocked_pair(
    session: AsyncSession, user_a_id: uuid.UUID, user_b_id: uuid.UUID
) -> bool:
    friendship = await find_pair_friendship(session, user_a_id, user_b_id)
    return friendship is not None and friendship.status == FriendshipStatus.BLOCKED
