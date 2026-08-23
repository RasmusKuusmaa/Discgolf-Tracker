from dataclasses import dataclass
from typing import Any

from app.models.achievement import Achievement


@dataclass
class UserGameStats:
    rounds_played: int
    distinct_courses_played: int
    courses_created: int
    total_birdies: int
    total_aces: int
    round_score_to_par: int
    round_birdies: int
    distinct_months_played: int
    current_streak_days: int
    beat_friend_personal_best: bool


@dataclass
class AchievementProgress:
    achievement: Achievement
    progress: float
    unlocked: bool


def _progress_and_met(criteria: dict[str, Any], stats: UserGameStats) -> tuple[float, bool]:
    criteria_type = criteria.get("type")

    if criteria_type == "rounds_played":
        target = criteria["count"]
        return min(stats.rounds_played / target, 1.0), stats.rounds_played >= target

    if criteria_type == "distinct_courses_played":
        target = criteria["count"]
        return (
            min(stats.distinct_courses_played / target, 1.0),
            stats.distinct_courses_played >= target,
        )

    if criteria_type == "courses_created":
        target = criteria["count"]
        return min(stats.courses_created / target, 1.0), stats.courses_created >= target

    if criteria_type == "score_term":
        target = criteria["count"]
        current = stats.total_aces if criteria["term"] == "ace" else stats.total_birdies
        return min(current / target, 1.0), current >= target

    if criteria_type == "round_score_to_par":
        met = stats.round_score_to_par <= criteria["max"]
        return (1.0 if met else 0.0), met

    if criteria_type == "birdies_in_single_round":
        target = criteria["count"]
        return min(stats.round_birdies / target, 1.0), stats.round_birdies >= target

    if criteria_type == "distinct_months_played":
        target = criteria["count"]
        return (
            min(stats.distinct_months_played / target, 1.0),
            stats.distinct_months_played >= target,
        )

    if criteria_type == "beat_friend_personal_best":
        met = stats.beat_friend_personal_best
        return (1.0 if met else 0.0), met

    if criteria_type == "play_streak":
        target = criteria["days"]
        return min(stats.current_streak_days / target, 1.0), stats.current_streak_days >= target

    return 0.0, False


def evaluate_achievements(
    stats: UserGameStats, achievements: list[Achievement]
) -> list[AchievementProgress]:
    results = []
    for achievement in achievements:
        progress, unlocked = _progress_and_met(achievement.criteria, stats)
        results.append(
            AchievementProgress(achievement=achievement, progress=progress, unlocked=unlocked)
        )
    return results
