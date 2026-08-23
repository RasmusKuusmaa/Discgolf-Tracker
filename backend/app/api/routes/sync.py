import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import ColumnElement, Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.achievement import Achievement
from app.models.course import Course
from app.models.friendship import Friendship
from app.models.hole import Hole
from app.models.hole_score import HoleScore
from app.models.layout import Layout
from app.models.round import Round
from app.models.round_player import RoundPlayer
from app.models.user import User
from app.models.user_achievement import UserAchievement
from app.schemas.geo import coordinates_from_geography
from app.schemas.sync import (
    SyncCourse,
    SyncFriendship,
    SyncHole,
    SyncHoleScore,
    SyncLayout,
    SyncPullResponse,
    SyncRound,
    SyncRoundPlayer,
    SyncUserAchievement,
)

router = APIRouter(prefix="/sync", tags=["sync"])


def _since_clause(model: Any, since: datetime | None) -> ColumnElement[bool]:
    if since is None:
        return model.deleted_at.is_(None)  # type: ignore[no-any-return]
    return model.updated_at > since  # type: ignore[no-any-return]


def _to_sync_course(course: Course) -> SyncCourse:
    return SyncCourse(
        id=course.id,
        name=course.name,
        slug=course.slug,
        description=course.description,
        city=course.city,
        region=course.region,
        country=course.country,
        location=coordinates_from_geography(course.location),
        created_by_id=course.created_by_id,
        visibility=course.visibility,
        status=course.status,
        osm_id=course.osm_id,
        is_verified=course.is_verified,
        updated_at=course.updated_at,
        deleted=course.deleted_at is not None,
    )


def _to_sync_layout(layout: Layout) -> SyncLayout:
    return SyncLayout(
        id=layout.id,
        course_id=layout.course_id,
        name=layout.name,
        hole_count=layout.hole_count,
        par_total=layout.par_total,
        total_distance_m=layout.total_distance_m,
        difficulty=layout.difficulty,
        is_default=layout.is_default,
        is_active=layout.is_active,
        updated_at=layout.updated_at,
        deleted=layout.deleted_at is not None,
    )


def _to_sync_hole(hole: Hole) -> SyncHole:
    return SyncHole(
        id=hole.id,
        layout_id=hole.layout_id,
        number=hole.number,
        par=hole.par,
        distance_m=hole.distance_m,
        tee_location=coordinates_from_geography(hole.tee_location),
        basket_location=coordinates_from_geography(hole.basket_location),
        elevation_delta_m=hole.elevation_delta_m,
        notes=hole.notes,
        updated_at=hole.updated_at,
        deleted=hole.deleted_at is not None,
    )


def _to_sync_round(round_: Round) -> SyncRound:
    return SyncRound(
        id=round_.id,
        layout_id=round_.layout_id,
        created_by_id=round_.created_by_id,
        started_at=round_.started_at,
        completed_at=round_.completed_at,
        status=round_.status,
        is_practice=round_.is_practice,
        weather_note=round_.weather_note,
        client_generated=round_.client_generated,
        is_partial=round_.is_partial,
        updated_at=round_.updated_at,
        deleted=round_.deleted_at is not None,
        players=[
            SyncRoundPlayer(
                id=player.id,
                round_id=player.round_id,
                user_id=player.user_id,
                guest_name=player.guest_name,
                position=player.position,
                is_scorekeeper=player.is_scorekeeper,
            )
            for player in round_.players
        ],
    )


def _to_sync_hole_score(hole_score: HoleScore) -> SyncHoleScore:
    return SyncHoleScore(
        id=hole_score.id,
        round_id=hole_score.round_id,
        round_player_id=hole_score.round_player_id,
        hole_id=hole_score.hole_id,
        strokes=hole_score.strokes,
        penalty_strokes=hole_score.penalty_strokes,
        is_circle_hit=hole_score.is_circle_hit,
        is_fairway_hit=hole_score.is_fairway_hit,
        notes=hole_score.notes,
        updated_at=hole_score.updated_at,
        deleted=hole_score.deleted_at is not None,
    )


def _to_sync_friendship(friendship: Friendship) -> SyncFriendship:
    return SyncFriendship(
        id=friendship.id,
        requester_id=friendship.requester_id,
        addressee_id=friendship.addressee_id,
        status=friendship.status,
        responded_at=friendship.responded_at,
        updated_at=friendship.updated_at,
        deleted=friendship.deleted_at is not None,
    )


def _to_sync_user_achievement(
    user_achievement: UserAchievement, achievement_code: str
) -> SyncUserAchievement:
    return SyncUserAchievement(
        id=user_achievement.id,
        achievement_id=user_achievement.achievement_id,
        achievement_code=achievement_code,
        unlocked_at=user_achievement.unlocked_at,
        progress=float(user_achievement.progress),
        updated_at=user_achievement.updated_at,
        deleted=user_achievement.deleted_at is not None,
    )


async def _pull_courses(session: AsyncSession, since: datetime | None) -> list[SyncCourse]:
    stmt: Select[tuple[Course]] = select(Course).where(_since_clause(Course, since))
    rows = (await session.execute(stmt)).scalars().all()
    return [_to_sync_course(row) for row in rows]


async def _pull_layouts(session: AsyncSession, since: datetime | None) -> list[SyncLayout]:
    stmt: Select[tuple[Layout]] = select(Layout).where(_since_clause(Layout, since))
    rows = (await session.execute(stmt)).scalars().all()
    return [_to_sync_layout(row) for row in rows]


async def _pull_holes(session: AsyncSession, since: datetime | None) -> list[SyncHole]:
    stmt: Select[tuple[Hole]] = select(Hole).where(_since_clause(Hole, since))
    rows = (await session.execute(stmt)).scalars().all()
    return [_to_sync_hole(row) for row in rows]


async def _pull_rounds(
    session: AsyncSession, user_id: uuid.UUID, since: datetime | None
) -> list[SyncRound]:
    user_round_ids = select(RoundPlayer.round_id).where(RoundPlayer.user_id == user_id)
    stmt: Select[tuple[Round]] = (
        select(Round)
        .where(Round.id.in_(user_round_ids))
        .where(_since_clause(Round, since))
        .options(selectinload(Round.players))
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_to_sync_round(row) for row in rows]


async def _pull_hole_scores(
    session: AsyncSession, user_id: uuid.UUID, since: datetime | None
) -> list[SyncHoleScore]:
    user_round_ids = select(RoundPlayer.round_id).where(RoundPlayer.user_id == user_id)
    stmt: Select[tuple[HoleScore]] = (
        select(HoleScore)
        .where(HoleScore.round_id.in_(user_round_ids))
        .where(_since_clause(HoleScore, since))
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_to_sync_hole_score(row) for row in rows]


async def _pull_friendships(
    session: AsyncSession, user_id: uuid.UUID, since: datetime | None
) -> list[SyncFriendship]:
    stmt: Select[tuple[Friendship]] = (
        select(Friendship)
        .where(or_(Friendship.requester_id == user_id, Friendship.addressee_id == user_id))
        .where(_since_clause(Friendship, since))
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_to_sync_friendship(row) for row in rows]


async def _pull_user_achievements(
    session: AsyncSession, user_id: uuid.UUID, since: datetime | None
) -> list[SyncUserAchievement]:
    stmt = (
        select(UserAchievement, Achievement.code)
        .join(Achievement, Achievement.id == UserAchievement.achievement_id)
        .where(UserAchievement.user_id == user_id)
        .where(_since_clause(UserAchievement, since))
    )
    rows = (await session.execute(stmt)).all()
    return [_to_sync_user_achievement(row.UserAchievement, row.code) for row in rows]


@router.get("/pull", response_model=SyncPullResponse)
async def pull_sync(
    since: datetime | None = Query(default=None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SyncPullResponse:
    cursor = datetime.now(UTC)

    return SyncPullResponse(
        cursor=cursor,
        courses=await _pull_courses(session, since),
        layouts=await _pull_layouts(session, since),
        holes=await _pull_holes(session, since),
        rounds=await _pull_rounds(session, user.id, since),
        scores=await _pull_hole_scores(session, user.id, since),
        friends=await _pull_friendships(session, user.id, since),
        achievements=await _pull_user_achievements(session, user.id, since),
    )
