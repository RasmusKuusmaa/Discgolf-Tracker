from datetime import date, datetime

from pydantic import BaseModel


class AchievementSummary(BaseModel):
    code: str
    name: str
    description: str
    icon: str
    category: str
    tier: int
    xp_reward: int
    unlocked: bool
    unlocked_at: datetime | None
    progress: float


class GamificationProfile(BaseModel):
    level: int
    total_xp: int
    xp_to_next_level: int
    current_streak: int
    longest_streak: int
    last_played_date: date | None
    achievements: list[AchievementSummary]
