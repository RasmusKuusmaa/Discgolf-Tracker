import base64
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.errors import AppError
from app.core.gamification import (
    XP_PERSONAL_BEST,
    award_participation_xp_for_round,
    award_xp,
    evaluate_achievements_for_round,
    get_total_xp,
    update_play_streaks_for_round,
)
from app.core.leveling import level_for_xp
from app.core.scoring import score_term
from app.db.session import get_session
from app.models.hole import Hole
from app.models.hole_score import HoleScore
from app.models.layout import Layout
from app.models.personal_best import PersonalBest
from app.models.round import Round, RoundStatus
from app.models.round_player import RoundPlayer
from app.models.user import User
from app.models.user_layout_stats import UserLayoutStats
from app.schemas.hole_score import HoleScoreUpsert, RoundScoresResponse, RoundScoresUpsert
from app.schemas.round import (
    RewardedAchievement,
    RewardedPersonalBest,
    RoundCompleteResponse,
    RoundCreate,
    RoundDetailResponse,
    RoundListResponse,
    RoundRead,
    RoundRewards,
    ScorecardHoleScore,
    ScorecardPlayer,
)

router = APIRouter(prefix="/rounds", tags=["rounds"])


def _round_with_players_stmt() -> Select[tuple[Round]]:
    return select(Round).options(selectinload(Round.players))


def _encode_cursor(round_id: uuid.UUID) -> str:
    return base64.urlsafe_b64encode(str(round_id).encode()).decode()


def _decode_cursor(cursor: str) -> uuid.UUID:
    try:
        return uuid.UUID(base64.urlsafe_b64decode(cursor.encode()).decode())
    except (ValueError, UnicodeDecodeError) as exc:
        raise AppError(
            "invalid_cursor", "Invalid pagination cursor", status.HTTP_400_BAD_REQUEST
        ) from exc


async def _get_owned_round(session: AsyncSession, round_id: uuid.UUID, user: User) -> Round:
    result = await session.execute(
        select(Round).where(Round.id == round_id, Round.deleted_at.is_(None))
    )
    round_ = result.scalar_one_or_none()
    if round_ is None:
        raise AppError("round_not_found", "Round not found", status.HTTP_404_NOT_FOUND)
    if round_.created_by_id != user.id and not user.is_admin:
        raise AppError(
            "not_round_owner",
            "Only the round creator or an admin can do this",
            status.HTTP_403_FORBIDDEN,
        )
    return round_


@router.post("", response_model=RoundRead, status_code=status.HTTP_201_CREATED)
async def create_round(
    payload: RoundCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Round:
    layout_result = await session.execute(
        select(Layout).where(Layout.id == payload.layout_id, Layout.deleted_at.is_(None))
    )
    if layout_result.scalar_one_or_none() is None:
        raise AppError("layout_not_found", "Layout not found", status.HTTP_404_NOT_FOUND)

    user_ids = {p.user_id for p in payload.players if p.user_id is not None}
    if user_ids:
        found = await session.execute(select(User.id).where(User.id.in_(user_ids)))
        found_ids = set(found.scalars())
        missing = user_ids - found_ids
        if missing:
            raise AppError(
                "player_not_found",
                f"Unknown user id(s): {', '.join(str(m) for m in missing)}",
                status.HTTP_404_NOT_FOUND,
            )

    round_ = Round(
        id=payload.id,
        layout_id=payload.layout_id,
        created_by_id=user.id,
        started_at=payload.started_at or datetime.now(UTC),
        is_practice=payload.is_practice,
        weather_note=payload.weather_note,
        client_generated=payload.client_generated,
    )
    for player_in in payload.players:
        round_.players.append(
            RoundPlayer(
                id=player_in.id,
                user_id=player_in.user_id,
                guest_name=player_in.guest_name,
                position=player_in.position,
                is_scorekeeper=player_in.is_scorekeeper,
            )
        )

    session.add(round_)
    await session.commit()

    result = await session.execute(_round_with_players_stmt().where(Round.id == round_.id))
    return result.scalar_one()


@router.get("", response_model=RoundListResponse)
async def list_rounds(
    layout_id: uuid.UUID | None = None,
    course_id: uuid.UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> RoundListResponse:
    stmt = select(Round).where(Round.created_by_id == user.id, Round.deleted_at.is_(None))

    if layout_id is not None:
        stmt = stmt.where(Round.layout_id == layout_id)
    if course_id is not None:
        stmt = stmt.where(
            Round.layout_id.in_(select(Layout.id).where(Layout.course_id == course_id))
        )
    if date_from is not None:
        stmt = stmt.where(Round.started_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Round.started_at <= date_to)
    if cursor:
        stmt = stmt.where(Round.id < _decode_cursor(cursor))

    stmt = stmt.order_by(Round.id.desc()).limit(limit + 1)

    result = await session.execute(stmt)
    rounds = list(result.scalars())

    has_more = len(rounds) > limit
    rounds = rounds[:limit]
    next_cursor = _encode_cursor(rounds[-1].id) if has_more and rounds else None

    return RoundListResponse(items=rounds, next_cursor=next_cursor)


def _build_scorecard_player(
    player: RoundPlayer, holes_by_id: dict[uuid.UUID, Hole]
) -> ScorecardPlayer:
    ordered_scores = sorted(player.hole_scores, key=lambda s: holes_by_id[s.hole_id].number)

    scores = []
    running_total = 0
    for score in ordered_scores:
        hole = holes_by_id[score.hole_id]
        running_total += score.strokes + score.penalty_strokes
        scores.append(
            ScorecardHoleScore(
                hole_id=score.hole_id,
                hole_number=hole.number,
                par=hole.par,
                strokes=score.strokes,
                penalty_strokes=score.penalty_strokes,
                diff_to_par=score.strokes + score.penalty_strokes - hole.par,
                running_total=running_total,
                term=score_term(score.strokes, score.penalty_strokes, hole.par),
                is_circle_hit=score.is_circle_hit,
                is_fairway_hit=score.is_fairway_hit,
                notes=score.notes,
            )
        )

    return ScorecardPlayer(
        id=player.id,
        user_id=player.user_id,
        guest_name=player.guest_name,
        position=player.position,
        is_scorekeeper=player.is_scorekeeper,
        total_strokes=sum(s.strokes for s in scores),
        total_penalties=sum(s.penalty_strokes for s in scores),
        score_to_par=sum(s.diff_to_par for s in scores),
        scores=scores,
    )


@router.get("/{round_id}", response_model=RoundDetailResponse)
async def get_round(
    round_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> RoundDetailResponse:
    round_ = await _get_owned_round(session, round_id, user)

    result = await session.execute(
        select(Round)
        .options(
            selectinload(Round.layout).selectinload(Layout.holes),
            selectinload(Round.players).selectinload(RoundPlayer.hole_scores),
        )
        .where(Round.id == round_.id)
    )
    round_ = result.scalar_one()

    holes_by_id = {hole.id: hole for hole in round_.layout.holes}
    players = [_build_scorecard_player(player, holes_by_id) for player in round_.players]

    return RoundDetailResponse(
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
        created_at=round_.created_at,
        layout=round_.layout,
        players=players,
    )


async def _validate_scorecard_refs(
    session: AsyncSession, round_: Round, scores: list[HoleScoreUpsert]
) -> None:
    player_ids = {s.round_player_id for s in scores}
    hole_ids = {s.hole_id for s in scores}

    valid_players = await session.execute(
        select(RoundPlayer.id).where(
            RoundPlayer.round_id == round_.id, RoundPlayer.id.in_(player_ids)
        )
    )
    missing_players = player_ids - set(valid_players.scalars())
    if missing_players:
        raise AppError(
            "player_not_in_round",
            f"round_player_id(s) not on this round: "
            f"{', '.join(str(p) for p in missing_players)}",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    valid_holes = await session.execute(
        select(Hole.id).where(Hole.layout_id == round_.layout_id, Hole.id.in_(hole_ids))
    )
    missing_holes = hole_ids - set(valid_holes.scalars())
    if missing_holes:
        raise AppError(
            "hole_not_in_layout",
            f"hole_id(s) not part of this round's layout: "
            f"{', '.join(str(h) for h in missing_holes)}",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )


@router.put("/{round_id}/scores", response_model=RoundScoresResponse)
async def upsert_round_scores(
    round_id: uuid.UUID,
    payload: RoundScoresUpsert,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> RoundScoresResponse:
    round_ = await _get_owned_round(session, round_id, user)
    if round_.status != RoundStatus.IN_PROGRESS and not user.is_admin:
        raise AppError(
            "round_not_in_progress",
            "Cannot write scores to a round that is not in progress",
            status.HTTP_409_CONFLICT,
        )
    await _validate_scorecard_refs(session, round_, payload.scores)

    for score_in in payload.scores:
        existing = await session.execute(
            select(HoleScore).where(
                HoleScore.round_player_id == score_in.round_player_id,
                HoleScore.hole_id == score_in.hole_id,
            )
        )
        hole_score = existing.scalar_one_or_none()

        if hole_score is None:
            hole_score = HoleScore(
                id=score_in.id,
                round_id=round_.id,
                round_player_id=score_in.round_player_id,
                hole_id=score_in.hole_id,
            )
            session.add(hole_score)

        hole_score.strokes = score_in.strokes
        hole_score.penalty_strokes = score_in.penalty_strokes
        hole_score.is_circle_hit = score_in.is_circle_hit
        hole_score.is_fairway_hit = score_in.is_fairway_hit
        hole_score.notes = score_in.notes

    await session.commit()

    all_scores = await session.execute(
        select(HoleScore).join(RoundPlayer).where(RoundPlayer.round_id == round_.id)
    )
    return RoundScoresResponse(scores=list(all_scores.scalars()))


@router.post("/{round_id}/complete", response_model=RoundCompleteResponse)
async def complete_round(
    round_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> RoundCompleteResponse:
    round_ = await _get_owned_round(session, round_id, user)
    if round_.status != RoundStatus.IN_PROGRESS:
        raise AppError(
            "round_not_in_progress", "Round is not in progress", status.HTTP_409_CONFLICT
        )

    player_count = await session.execute(
        select(func.count(RoundPlayer.id)).where(RoundPlayer.round_id == round_.id)
    )
    hole_count = await session.execute(
        select(func.count(Hole.id)).where(Hole.layout_id == round_.layout_id)
    )
    expected_scores = player_count.scalar_one() * hole_count.scalar_one()

    actual_scores = await session.execute(
        select(func.count(HoleScore.id)).where(HoleScore.round_id == round_.id)
    )

    round_.is_partial = actual_scores.scalar_one() < expected_scores
    round_.status = RoundStatus.COMPLETED
    round_.completed_at = datetime.now(UTC)

    xp_before = await get_total_xp(session, user.id)
    new_achievements: list[RewardedAchievement] = []
    new_personal_bests: list[RewardedPersonalBest] = []

    if not round_.is_partial and not round_.is_practice:
        await _update_stats_after_completion(session, round_)
        await update_play_streaks_for_round(session, round_)
        await award_participation_xp_for_round(session, round_)
        newly_unlocked_by_user = await evaluate_achievements_for_round(session, round_)

        new_achievements = [
            RewardedAchievement(
                code=achievement.code,
                name=achievement.name,
                icon=achievement.icon,
                xp_reward=achievement.xp_reward,
            )
            for achievement in newly_unlocked_by_user.get(user.id, [])
        ]

        pb_result = await session.execute(
            select(PersonalBest).where(
                PersonalBest.user_id == user.id, PersonalBest.layout_id == round_.layout_id
            )
        )
        personal_best = pb_result.scalar_one_or_none()
        if personal_best is not None and personal_best.round_id == round_.id:
            new_personal_bests = [
                RewardedPersonalBest(
                    layout_id=round_.layout_id, best_score_to_par=personal_best.best_score_to_par
                )
            ]

    xp_after = await get_total_xp(session, user.id)
    level_before = level_for_xp(xp_before)
    level_after = level_for_xp(xp_after)

    await session.commit()

    result = await session.execute(_round_with_players_stmt().where(Round.id == round_.id))
    round_obj = result.scalar_one()

    rewards = RoundRewards(
        xp_gained=xp_after - xp_before,
        level_up=level_after > level_before,
        new_level=level_after,
        new_achievements=new_achievements,
        new_personal_bests=new_personal_bests,
    )

    response = RoundCompleteResponse(
        **RoundRead.model_validate(round_obj).model_dump(), rewards=rewards
    )
    return response


async def _update_personal_best(
    session: AsyncSession, round_: Round, player: RoundPlayer, score_to_par: int
) -> None:
    existing_result = await session.execute(
        select(PersonalBest).where(
            PersonalBest.user_id == player.user_id,
            PersonalBest.layout_id == round_.layout_id,
        )
    )
    personal_best = existing_result.scalar_one_or_none()

    user_id = player.user_id
    assert user_id is not None

    if personal_best is None:
        session.add(
            PersonalBest(
                user_id=user_id,
                layout_id=round_.layout_id,
                best_score_to_par=score_to_par,
                round_id=round_.id,
                achieved_at=datetime.now(UTC),
            )
        )
        await award_xp(session, user_id, "personal_best", XP_PERSONAL_BEST, round_.layout_id)
    elif score_to_par < personal_best.best_score_to_par:
        personal_best.best_score_to_par = score_to_par
        personal_best.round_id = round_.id
        personal_best.achieved_at = datetime.now(UTC)
        await award_xp(session, user_id, "personal_best", XP_PERSONAL_BEST, round_.layout_id)


async def _update_layout_stats(
    session: AsyncSession, round_: Round, player: RoundPlayer, score_to_par: int
) -> None:
    existing_result = await session.execute(
        select(UserLayoutStats).where(
            UserLayoutStats.user_id == player.user_id,
            UserLayoutStats.layout_id == round_.layout_id,
        )
    )
    stats = existing_result.scalar_one_or_none()

    if stats is None:
        session.add(
            UserLayoutStats(
                user_id=player.user_id,
                layout_id=round_.layout_id,
                rounds_played=1,
                total_score_to_par=score_to_par,
                best_score_to_par=score_to_par,
                last_played_at=round_.completed_at or datetime.now(UTC),
            )
        )
    else:
        stats.rounds_played += 1
        stats.total_score_to_par += score_to_par
        if stats.best_score_to_par is None or score_to_par < stats.best_score_to_par:
            stats.best_score_to_par = score_to_par
        stats.last_played_at = round_.completed_at or datetime.now(UTC)


async def _update_stats_after_completion(session: AsyncSession, round_: Round) -> None:
    layout = await session.get(Layout, round_.layout_id)
    if layout is None:
        return

    players_result = await session.execute(
        select(RoundPlayer).where(
            RoundPlayer.round_id == round_.id, RoundPlayer.user_id.is_not(None)
        )
    )

    for player in players_result.scalars():
        total_result = await session.execute(
            select(func.sum(HoleScore.strokes + HoleScore.penalty_strokes)).where(
                HoleScore.round_player_id == player.id
            )
        )
        total = total_result.scalar_one() or 0
        score_to_par = total - layout.par_total

        await _update_personal_best(session, round_, player, score_to_par)
        await _update_layout_stats(session, round_, player, score_to_par)


@router.post("/{round_id}/abandon", response_model=RoundRead)
async def abandon_round(
    round_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Round:
    round_ = await _get_owned_round(session, round_id, user)
    if round_.status != RoundStatus.IN_PROGRESS:
        raise AppError(
            "round_not_in_progress", "Round is not in progress", status.HTTP_409_CONFLICT
        )

    round_.status = RoundStatus.ABANDONED
    await session.commit()

    result = await session.execute(_round_with_players_stmt().where(Round.id == round_.id))
    return result.scalar_one()
