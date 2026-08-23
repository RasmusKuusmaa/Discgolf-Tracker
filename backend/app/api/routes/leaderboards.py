import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import AppError
from app.core.friendships import accepted_friend_ids
from app.db.session import get_session
from app.models.layout import Layout
from app.models.personal_best import PersonalBest
from app.models.user import User
from app.schemas.friendship import FriendSummary
from app.schemas.leaderboard import LeaderboardEntry, LeaderboardResponse

router = APIRouter(prefix="/leaderboards", tags=["leaderboards"])

_VALID_SCOPES = {"friends", "global"}


@router.get("/layouts/{layout_id}", response_model=LeaderboardResponse)
async def get_layout_leaderboard(
    layout_id: uuid.UUID,
    scope: str = Query(default="global"),
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LeaderboardResponse:
    if scope not in _VALID_SCOPES:
        raise AppError(
            "invalid_scope",
            f"scope must be one of {sorted(_VALID_SCOPES)}",
            status.HTTP_400_BAD_REQUEST,
        )

    layout = await session.get(Layout, layout_id)
    if layout is None or layout.deleted_at is not None:
        raise AppError("layout_not_found", "Layout not found", status.HTTP_404_NOT_FOUND)

    stmt = select(PersonalBest).where(
        PersonalBest.layout_id == layout_id, PersonalBest.deleted_at.is_(None)
    )

    if scope == "friends":
        friend_ids = await accepted_friend_ids(session, user.id)
        stmt = stmt.where(PersonalBest.user_id.in_({*friend_ids, user.id}))

    stmt = stmt.order_by(
        PersonalBest.best_score_to_par.asc(), PersonalBest.achieved_at.asc()
    ).limit(limit)

    rows = list((await session.execute(stmt)).scalars())
    user_ids = [row.user_id for row in rows]
    users_by_id = {
        u.id: u
        for u in (await session.execute(select(User).where(User.id.in_(user_ids)))).scalars()
    }

    entries = [
        LeaderboardEntry(
            rank=rank,
            user=FriendSummary.model_validate(users_by_id[row.user_id]),
            best_score_to_par=row.best_score_to_par,
            achieved_at=row.achieved_at,
        )
        for rank, row in enumerate(rows, start=1)
        if row.user_id in users_by_id
    ]

    return LeaderboardResponse(layout_id=layout_id, scope=scope, entries=entries)
