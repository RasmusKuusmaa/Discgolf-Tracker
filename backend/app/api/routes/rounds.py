import base64
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.errors import AppError
from app.db.session import get_session
from app.models.hole import Hole
from app.models.hole_score import HoleScore
from app.models.layout import Layout
from app.models.round import Round, RoundStatus
from app.models.round_player import RoundPlayer
from app.models.user import User
from app.schemas.hole_score import HoleScoreUpsert, RoundScoresResponse, RoundScoresUpsert
from app.schemas.round import RoundCreate, RoundListResponse, RoundRead

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
    if round_.created_by_id != user.id:
        raise AppError(
            "not_round_owner",
            "Only the round creator can do this",
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


@router.post("/{round_id}/complete", response_model=RoundRead)
async def complete_round(
    round_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Round:
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
    await session.commit()

    result = await session.execute(_round_with_players_stmt().where(Round.id == round_.id))
    return result.scalar_one()


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
