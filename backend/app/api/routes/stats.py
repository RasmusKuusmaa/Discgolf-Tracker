import uuid
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import AppError
from app.core.scoring import score_term
from app.db.session import get_session
from app.models.hole import Hole
from app.models.hole_score import HoleScore
from app.models.layout import Layout
from app.models.round import Round, RoundStatus
from app.models.round_player import RoundPlayer
from app.models.user import User
from app.schemas.stats import (
    BestRound,
    HoleStats,
    LayoutHoleAverage,
    LayoutStats,
    LayoutTrendPoint,
    ScoreDistribution,
    StatsSummary,
    TrendPoint,
    TrendResponse,
)

_VALID_TREND_PERIODS = {"week", "month", "year"}

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


@router.get("/layouts/{layout_id}", response_model=LayoutStats)
async def get_layout_stats(
    layout_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LayoutStats:
    layout = await session.get(Layout, layout_id)
    if layout is None or layout.deleted_at is not None:
        raise AppError("layout_not_found", "Layout not found", status.HTTP_404_NOT_FOUND)

    rows_stmt = (
        select(
            Round.id,
            Round.completed_at,
            Hole.id,
            Hole.number,
            Hole.par,
            HoleScore.strokes,
            HoleScore.penalty_strokes,
        )
        .select_from(Round)
        .join(RoundPlayer, RoundPlayer.round_id == Round.id)
        .join(HoleScore, HoleScore.round_player_id == RoundPlayer.id)
        .join(Hole, Hole.id == HoleScore.hole_id)
        .where(
            RoundPlayer.user_id == user.id,
            Round.layout_id == layout_id,
            Round.status == RoundStatus.COMPLETED,
        )
    )
    rows = (await session.execute(rows_stmt)).all()

    round_totals: dict[uuid.UUID, int] = defaultdict(int)
    round_completed_at: dict[uuid.UUID, datetime] = {}
    hole_totals: dict[uuid.UUID, int] = defaultdict(int)
    hole_attempts: dict[uuid.UUID, int] = defaultdict(int)
    hole_info: dict[uuid.UUID, tuple[int, int]] = {}

    for round_id, completed_at, hole_id, number, par, strokes, penalty_strokes in rows:
        round_totals[round_id] += strokes + penalty_strokes - par
        round_completed_at[round_id] = completed_at
        hole_totals[hole_id] += strokes + penalty_strokes
        hole_attempts[hole_id] += 1
        hole_info[hole_id] = (number, par)

    rounds_played = len(round_totals)
    best_score_to_par = min(round_totals.values()) if round_totals else None
    average_score_to_par = (
        (sum(round_totals.values()) / rounds_played) if rounds_played else None
    )

    trend_round_ids = sorted(round_totals, key=lambda rid: round_completed_at[rid])[-10:]
    trend = [
        LayoutTrendPoint(
            round_id=round_id,
            completed_at=round_completed_at[round_id],
            score_to_par=round_totals[round_id],
        )
        for round_id in trend_round_ids
    ]

    hole_averages = sorted(
        (
            LayoutHoleAverage(
                hole_id=hole_id,
                hole_number=number,
                par=par,
                average_strokes=hole_totals[hole_id] / hole_attempts[hole_id],
                attempts=hole_attempts[hole_id],
            )
            for hole_id, (number, par) in hole_info.items()
        ),
        key=lambda h: h.hole_number,
    )

    return LayoutStats(
        layout_id=layout_id,
        rounds_played=rounds_played,
        best_score_to_par=best_score_to_par,
        average_score_to_par=average_score_to_par,
        trend=trend,
        hole_averages=hole_averages,
    )


@router.get("/holes/{hole_id}", response_model=HoleStats)
async def get_hole_stats(
    hole_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> HoleStats:
    hole = await session.get(Hole, hole_id)
    if hole is None:
        raise AppError("hole_not_found", "Hole not found", status.HTTP_404_NOT_FOUND)

    rows_stmt = (
        select(HoleScore.strokes, HoleScore.penalty_strokes)
        .select_from(HoleScore)
        .join(RoundPlayer, RoundPlayer.id == HoleScore.round_player_id)
        .join(Round, Round.id == RoundPlayer.round_id)
        .where(
            HoleScore.hole_id == hole_id,
            RoundPlayer.user_id == user.id,
            Round.status == RoundStatus.COMPLETED,
        )
    )
    rows = (await session.execute(rows_stmt)).all()

    distribution = ScoreDistribution()
    totals = []
    for strokes, penalty_strokes in rows:
        totals.append(strokes + penalty_strokes)
        term = score_term(strokes, penalty_strokes, hole.par)
        setattr(distribution, term, getattr(distribution, term) + 1)

    return HoleStats(
        hole_id=hole_id,
        par=hole.par,
        attempts=len(totals),
        average_strokes=(sum(totals) / len(totals)) if totals else None,
        best_strokes=min(totals) if totals else None,
        score_distribution=distribution,
    )


def _period_start(completed_at: datetime, period: str) -> datetime:
    day_start = completed_at.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "year":
        return day_start.replace(month=1, day=1)
    if period == "month":
        return day_start.replace(day=1)
    return day_start - timedelta(days=day_start.weekday())


@router.get("/trend", response_model=TrendResponse)
async def get_trend(
    period: str = Query(default="month"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TrendResponse:
    if period not in _VALID_TREND_PERIODS:
        raise AppError(
            "invalid_period",
            f"period must be one of {sorted(_VALID_TREND_PERIODS)}",
            status.HTTP_400_BAD_REQUEST,
        )

    rows_stmt = (
        select(
            Round.id,
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
    for round_id, completed_at, strokes, penalty_strokes, par in rows:
        round_totals[round_id] += strokes + penalty_strokes - par
        round_completed_at[round_id] = completed_at

    bucket_totals: dict[datetime, int] = defaultdict(int)
    bucket_counts: dict[datetime, int] = defaultdict(int)
    for round_id, total in round_totals.items():
        bucket = _period_start(round_completed_at[round_id], period)
        bucket_totals[bucket] += total
        bucket_counts[bucket] += 1

    points = [
        TrendPoint(
            period_start=bucket,
            rounds_played=bucket_counts[bucket],
            avg_score_to_par=bucket_totals[bucket] / bucket_counts[bucket],
        )
        for bucket in sorted(bucket_totals)
    ]

    return TrendResponse(period=period, points=points)
