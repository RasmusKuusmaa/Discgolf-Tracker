import base64
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import AppError
from app.db.session import get_session
from app.models.course import Course
from app.models.friendship import Friendship, FriendshipStatus
from app.models.hole import Hole
from app.models.hole_score import HoleScore
from app.models.layout import Layout
from app.models.round import Round, RoundStatus
from app.models.round_player import RoundPlayer
from app.models.user import User, Visibility
from app.schemas.feed import FeedResponse, FeedRoundItem
from app.schemas.friendship import FriendSummary

router = APIRouter(tags=["feed"])


def _encode_feed_cursor(completed_at: datetime, round_id: uuid.UUID) -> str:
    raw = f"{completed_at.isoformat()}|{round_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_feed_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        completed_at_str, round_id_str = raw.rsplit("|", 1)
        return datetime.fromisoformat(completed_at_str), uuid.UUID(round_id_str)
    except (ValueError, UnicodeDecodeError) as exc:
        raise AppError(
            "invalid_cursor", "Invalid pagination cursor", status.HTTP_400_BAD_REQUEST
        ) from exc


async def _accepted_friend_ids(session: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    result = await session.execute(
        select(Friendship).where(
            Friendship.deleted_at.is_(None),
            Friendship.status == FriendshipStatus.ACCEPTED,
            or_(Friendship.requester_id == user_id, Friendship.addressee_id == user_id),
        )
    )
    return [
        f.addressee_id if f.requester_id == user_id else f.requester_id
        for f in result.scalars()
    ]


@router.get("/feed", response_model=FeedResponse)
async def get_feed(
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> FeedResponse:
    friend_ids = await _accepted_friend_ids(session, user.id)
    if not friend_ids:
        return FeedResponse(items=[])

    stmt = (
        select(
            Round.id.label("round_id"),
            Round.layout_id,
            Round.completed_at,
            Round.is_partial,
            RoundPlayer.id.label("round_player_id"),
            RoundPlayer.user_id,
            User.username,
            User.display_name,
            User.avatar_url,
            Course.name.label("course_name"),
        )
        .select_from(Round)
        .join(RoundPlayer, RoundPlayer.round_id == Round.id)
        .join(Layout, Layout.id == Round.layout_id)
        .join(Course, Course.id == Layout.course_id)
        .join(User, User.id == RoundPlayer.user_id)
        .where(
            RoundPlayer.user_id.in_(friend_ids),
            Round.status == RoundStatus.COMPLETED,
            User.stats_visibility != Visibility.PRIVATE,
        )
    )

    if cursor:
        completed_before, round_id_before = _decode_feed_cursor(cursor)
        stmt = stmt.where(
            or_(
                Round.completed_at < completed_before,
                and_(Round.completed_at == completed_before, Round.id < round_id_before),
            )
        )

    stmt = stmt.order_by(Round.completed_at.desc(), Round.id.desc()).limit(limit + 1)

    rows = (await session.execute(stmt)).all()
    has_more = len(rows) > limit
    rows = rows[:limit]

    round_player_ids = [row.round_player_id for row in rows]
    score_totals: dict[uuid.UUID, int] = {}
    if round_player_ids:
        totals_stmt = (
            select(
                HoleScore.round_player_id,
                func.sum(HoleScore.strokes + HoleScore.penalty_strokes - Hole.par),
            )
            .join(Hole, Hole.id == HoleScore.hole_id)
            .where(HoleScore.round_player_id.in_(round_player_ids))
            .group_by(HoleScore.round_player_id)
        )
        score_totals = {
            row_player_id: total for row_player_id, total in (await session.execute(totals_stmt))
        }

    items = [
        FeedRoundItem(
            round_id=row.round_id,
            user=FriendSummary(
                id=row.user_id,
                username=row.username,
                display_name=row.display_name,
                avatar_url=row.avatar_url,
            ),
            layout_id=row.layout_id,
            course_name=row.course_name,
            completed_at=row.completed_at,
            score_to_par=score_totals.get(row.round_player_id, 0),
            is_partial=row.is_partial,
        )
        for row in rows
    ]

    next_cursor = (
        _encode_feed_cursor(rows[-1].completed_at, rows[-1].round_id) if has_more and rows else None
    )

    return FeedResponse(items=items, next_cursor=next_cursor)
