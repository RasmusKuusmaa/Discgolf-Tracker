from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.errors import AppError
from app.db.session import get_session
from app.models.layout import Layout
from app.models.round import Round
from app.models.round_player import RoundPlayer
from app.models.user import User
from app.schemas.round import RoundCreate, RoundRead

router = APIRouter(prefix="/rounds", tags=["rounds"])


def _round_with_players_stmt() -> Select[tuple[Round]]:
    return select(Round).options(selectinload(Round.players))


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
