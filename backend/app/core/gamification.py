import uuid
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.achievements import AchievementProgress, UserGameStats, evaluate_achievements
from app.core.friendships import accepted_friend_ids
from app.core.scoring import score_term
from app.models.achievement import Achievement
from app.models.course import Course
from app.models.hole import Hole
from app.models.hole_score import HoleScore
from app.models.layout import Layout
from app.models.personal_best import PersonalBest
from app.models.round import Round, RoundStatus
from app.models.round_player import RoundPlayer
from app.models.user_achievement import UserAchievement
from app.models.xp_event import XpEvent

XP_ROUND_COMPLETED = 25
XP_PERSONAL_BEST = 50
XP_COURSE_CREATED = 20
XP_FIRST_COURSE_PLAY = 30


async def award_xp(
    session: AsyncSession,
    user_id: uuid.UUID,
    source: str,
    amount: int,
    ref_id: uuid.UUID | None = None,
) -> None:
    session.add(XpEvent(user_id=user_id, source=source, amount=amount, ref_id=ref_id))


def _compute_current_streak(play_days: list[date]) -> int:
    if not play_days:
        return 0
    streak = 1
    for i in range(len(play_days) - 1, 0, -1):
        if (play_days[i] - play_days[i - 1]).days == 1:
            streak += 1
        else:
            break
    return streak


async def _gather_user_game_stats(
    session: AsyncSession, user_id: uuid.UUID, round_: Round, round_player: RoundPlayer
) -> UserGameStats:
    completed_rounds_filter = (
        RoundPlayer.user_id == user_id,
        Round.status == RoundStatus.COMPLETED,
        Round.is_partial.is_(False),
        Round.is_practice.is_(False),
    )

    rounds_played = (
        await session.execute(
            select(func.count(func.distinct(Round.id)))
            .select_from(Round)
            .join(RoundPlayer, RoundPlayer.round_id == Round.id)
            .where(*completed_rounds_filter)
        )
    ).scalar_one()

    distinct_courses_played = (
        await session.execute(
            select(func.count(func.distinct(Layout.course_id)))
            .select_from(Round)
            .join(RoundPlayer, RoundPlayer.round_id == Round.id)
            .join(Layout, Layout.id == Round.layout_id)
            .where(*completed_rounds_filter)
        )
    ).scalar_one()

    courses_created = (
        await session.execute(
            select(func.count(Course.id)).where(
                Course.created_by_id == user_id, Course.deleted_at.is_(None)
            )
        )
    ).scalar_one()

    hole_rows = (
        await session.execute(
            select(HoleScore.strokes, HoleScore.penalty_strokes, Hole.par)
            .select_from(Round)
            .join(RoundPlayer, RoundPlayer.round_id == Round.id)
            .join(HoleScore, HoleScore.round_player_id == RoundPlayer.id)
            .join(Hole, Hole.id == HoleScore.hole_id)
            .where(*completed_rounds_filter)
        )
    ).all()
    total_birdies = sum(1 for s, p, par in hole_rows if score_term(s, p, par) == "birdie")
    total_aces = sum(1 for s, p, par in hole_rows if score_term(s, p, par) == "ace")

    completed_dates = (
        await session.execute(
            select(Round.completed_at)
            .join(RoundPlayer, RoundPlayer.round_id == Round.id)
            .where(*completed_rounds_filter)
        )
    ).scalars().all()
    play_days = sorted({d.date() for d in completed_dates if d is not None})
    distinct_months_played = len({(d.year, d.month) for d in play_days})
    current_streak_days = _compute_current_streak(play_days)

    this_round_rows = (
        await session.execute(
            select(HoleScore.strokes, HoleScore.penalty_strokes, Hole.par)
            .join(Hole, Hole.id == HoleScore.hole_id)
            .where(HoleScore.round_player_id == round_player.id)
        )
    ).all()
    round_score_to_par = sum(s + p - par for s, p, par in this_round_rows)
    round_birdies = sum(1 for s, p, par in this_round_rows if score_term(s, p, par) == "birdie")

    friend_ids = await accepted_friend_ids(session, user_id)
    beat_friend_personal_best = False
    if friend_ids:
        best_friend_score = (
            await session.execute(
                select(func.min(PersonalBest.best_score_to_par)).where(
                    PersonalBest.layout_id == round_.layout_id,
                    PersonalBest.user_id.in_(friend_ids),
                )
            )
        ).scalar_one()
        if best_friend_score is not None and round_score_to_par < best_friend_score:
            beat_friend_personal_best = True

    return UserGameStats(
        rounds_played=rounds_played,
        distinct_courses_played=distinct_courses_played,
        courses_created=courses_created,
        total_birdies=total_birdies,
        total_aces=total_aces,
        round_score_to_par=round_score_to_par,
        round_birdies=round_birdies,
        distinct_months_played=distinct_months_played,
        current_streak_days=current_streak_days,
        beat_friend_personal_best=beat_friend_personal_best,
    )


async def _apply_achievement_progress(
    session: AsyncSession, user_id: uuid.UUID, progresses: list[AchievementProgress]
) -> list[Achievement]:
    newly_unlocked: list[Achievement] = []

    for item in progresses:
        existing = await session.execute(
            select(UserAchievement).where(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == item.achievement.id,
            )
        )
        record = existing.scalar_one_or_none()

        if record is None:
            record = UserAchievement(
                user_id=user_id, achievement_id=item.achievement.id, progress=0.0
            )
            session.add(record)

        if record.unlocked_at is not None:
            continue

        record.progress = max(float(record.progress), item.progress)
        if item.unlocked:
            record.unlocked_at = datetime.now(UTC)
            record.progress = 1.0
            newly_unlocked.append(item.achievement)
            await award_xp(
                session,
                user_id,
                "achievement_unlocked",
                item.achievement.xp_reward,
                item.achievement.id,
            )

    return newly_unlocked


async def evaluate_achievements_for_round(
    session: AsyncSession, round_: Round
) -> dict[uuid.UUID, list[Achievement]]:
    achievements = list((await session.execute(select(Achievement))).scalars())
    if not achievements:
        return {}

    players_result = await session.execute(
        select(RoundPlayer).where(
            RoundPlayer.round_id == round_.id, RoundPlayer.user_id.is_not(None)
        )
    )

    newly_unlocked_by_user: dict[uuid.UUID, list[Achievement]] = {}
    for player in players_result.scalars():
        user_id = player.user_id
        assert user_id is not None
        stats = await _gather_user_game_stats(session, user_id, round_, player)
        progresses = evaluate_achievements(stats, achievements)
        newly_unlocked = await _apply_achievement_progress(session, user_id, progresses)
        if newly_unlocked:
            newly_unlocked_by_user[user_id] = newly_unlocked

    return newly_unlocked_by_user


async def award_participation_xp_for_round(session: AsyncSession, round_: Round) -> None:
    layout = await session.get(Layout, round_.layout_id)
    if layout is None:
        return

    players_result = await session.execute(
        select(RoundPlayer).where(
            RoundPlayer.round_id == round_.id, RoundPlayer.user_id.is_not(None)
        )
    )

    for player in players_result.scalars():
        user_id = player.user_id
        assert user_id is not None

        await award_xp(session, user_id, "round_completed", XP_ROUND_COMPLETED, round_.id)

        prior_play = await session.execute(
            select(Round.id)
            .select_from(Round)
            .join(RoundPlayer, RoundPlayer.round_id == Round.id)
            .join(Layout, Layout.id == Round.layout_id)
            .where(
                RoundPlayer.user_id == user_id,
                Layout.course_id == layout.course_id,
                Round.status == RoundStatus.COMPLETED,
                Round.is_partial.is_(False),
                Round.is_practice.is_(False),
                Round.id != round_.id,
            )
            .limit(1)
        )
        if prior_play.scalar_one_or_none() is None:
            await award_xp(
                session, user_id, "first_course_play", XP_FIRST_COURSE_PLAY, layout.course_id
            )
