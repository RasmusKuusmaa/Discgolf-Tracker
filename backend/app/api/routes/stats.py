import uuid
from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.scoring import score_term
from app.db.session import get_session
from app.models.hole import Hole
from app.models.hole_score import HoleScore
from app.models.layout import Layout
from app.models.round import Round, RoundStatus
from app.models.round_player import RoundPlayer
from app.models.user import User
from app.schemas.stats import BestRound, ScoreDistribution, StatsSummary

router = APIRouter(prefix="/stats/me", tags=["stats"])


@router.get("/summary", response_model=StatsSummary)
async def get_summary(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StatsSummary:
    played_stmt = (
        select(
            func.count(func.distinct(Round.id)),
            func.count(func.distinct(Round.layout_id)),
            func.count(func.distinct(Layout.course_id)),
        )
        .select_from(Round)
        .join(RoundPlayer, RoundPlayer.round_id == Round.id)
        .join(Layout, Layout.id == Round.layout_id)
        .where(RoundPlayer.user_id == user.id, Round.status == RoundStatus.COMPLETED)
    )
    rounds_played, layouts_played, courses_played = (await session.execute(played_stmt)).one()

    rows_stmt = (
        select(
            Round.id,
            Round.layout_id,
            Round.completed_at,
            HoleScore.strokes,
            HoleScore.penalty_strokes,
            Hole.par,
        )
        .select_from(Round)
        .join(RoundPlayer, RoundPlayer.round_id == Round.id)
        .join(HoleScore, HoleScore.round_player_id == RoundPlayer.id)
        .join(Hole, Hole.id == HoleScore.hole_id)
        .where(RoundPlayer.user_id == user.id, Round.status == RoundStatus.COMPLETED)
    )
    rows = (await session.execute(rows_stmt)).all()

    round_totals: dict[uuid.UUID, int] = defaultdict(int)
    round_completed_at: dict[uuid.UUID, datetime] = {}
    round_layout: dict[uuid.UUID, uuid.UUID] = {}
    distribution = ScoreDistribution()

    for round_id, layout_id, completed_at, strokes, penalty_strokes, par in rows:
        diff = strokes + penalty_strokes - par
        round_totals[round_id] += diff
        round_completed_at[round_id] = completed_at
        round_layout[round_id] = layout_id

        term = score_term(strokes, penalty_strokes, par)
        setattr(distribution, term, getattr(distribution, term) + 1)

    avg_score_to_par = (sum(round_totals.values()) / len(round_totals)) if round_totals else None

    best_round = None
    if round_totals:
        best_round_id = min(round_totals, key=lambda rid: round_totals[rid])
        best_round = BestRound(
            round_id=best_round_id,
            layout_id=round_layout[best_round_id],
            score_to_par=round_totals[best_round_id],
            completed_at=round_completed_at[best_round_id],
        )

    return StatsSummary(
        rounds_played=rounds_played,
        courses_played=courses_played,
        layouts_played=layouts_played,
        avg_score_to_par=avg_score_to_par,
        best_round=best_round,
        total_holes_played=len(rows),
        score_distribution=distribution,
    )
