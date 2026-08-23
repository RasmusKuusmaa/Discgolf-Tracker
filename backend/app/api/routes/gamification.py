from fastapi import APIRouter, Depends
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.gamification import get_total_xp
from app.core.leveling import level_for_xp, xp_to_next_level
from app.db.session import get_session
from app.models.achievement import Achievement
from app.models.play_streak import PlayStreak
from app.models.user import User
from app.models.user_achievement import UserAchievement
from app.schemas.gamification import AchievementSummary, GamificationProfile

router = APIRouter(prefix="/gamification", tags=["gamification"])


@router.get("/me", response_model=GamificationProfile)
async def get_gamification_profile(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GamificationProfile:
    total_xp = await get_total_xp(session, user.id)

    streak = (
        await session.execute(select(PlayStreak).where(PlayStreak.user_id == user.id))
    ).scalar_one_or_none()

    achievement_rows = (
        await session.execute(
            select(Achievement, UserAchievement)
            .outerjoin(
                UserAchievement,
                and_(
                    UserAchievement.achievement_id == Achievement.id,
                    UserAchievement.user_id == user.id,
                ),
            )
            .order_by(Achievement.category, Achievement.tier)
        )
    ).all()

    achievements = [
        AchievementSummary(
            code=achievement.code,
            name=achievement.name,
            description=achievement.description,
            icon=achievement.icon,
            category=achievement.category,
            tier=achievement.tier,
            xp_reward=achievement.xp_reward,
            unlocked=user_achievement is not None and user_achievement.unlocked_at is not None,
            unlocked_at=user_achievement.unlocked_at if user_achievement else None,
            progress=float(user_achievement.progress) if user_achievement else 0.0,
        )
        for achievement, user_achievement in achievement_rows
    ]

    return GamificationProfile(
        level=level_for_xp(total_xp),
        total_xp=total_xp,
        xp_to_next_level=xp_to_next_level(total_xp),
        current_streak=streak.current_streak if streak else 0,
        longest_streak=streak.longest_streak if streak else 0,
        last_played_date=streak.last_played_date if streak else None,
        achievements=achievements,
    )
