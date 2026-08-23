"""Seed the fixed set of v1 achievement definitions.

Idempotent: upserts by `code`, safe to run multiple times (e.g. on deploy).

Usage:
    uv run python scripts/seed_achievements.py
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.db.session import async_session_maker  # noqa: E402
from app.models.achievement import Achievement  # noqa: E402

ACHIEVEMENTS: list[dict[str, Any]] = [
    {
        "code": "first_round",
        "name": "Tee Off",
        "description": "Complete your first round.",
        "icon": "🥏",
        "category": "rounds",
        "tier": 1,
        "xp_reward": 50,
        "criteria": {"type": "rounds_played", "count": 1},
    },
    {
        "code": "rounds_10",
        "name": "Regular",
        "description": "Complete 10 rounds.",
        "icon": "🥏",
        "category": "rounds",
        "tier": 1,
        "xp_reward": 100,
        "criteria": {"type": "rounds_played", "count": 10},
    },
    {
        "code": "rounds_50",
        "name": "Dedicated",
        "description": "Complete 50 rounds.",
        "icon": "🥏",
        "category": "rounds",
        "tier": 2,
        "xp_reward": 250,
        "criteria": {"type": "rounds_played", "count": 50},
    },
    {
        "code": "rounds_100",
        "name": "Veteran",
        "description": "Complete 100 rounds.",
        "icon": "🥏",
        "category": "rounds",
        "tier": 3,
        "xp_reward": 500,
        "criteria": {"type": "rounds_played", "count": 100},
    },
    {
        "code": "first_birdie",
        "name": "Under Par",
        "description": "Score your first birdie.",
        "icon": "🐦",
        "category": "scoring",
        "tier": 1,
        "xp_reward": 50,
        "criteria": {"type": "score_term", "term": "birdie", "count": 1},
    },
    {
        "code": "first_ace",
        "name": "Ace!",
        "description": "Score your first hole-in-one.",
        "icon": "🎯",
        "category": "scoring",
        "tier": 1,
        "xp_reward": 200,
        "criteria": {"type": "score_term", "term": "ace", "count": 1},
    },
    {
        "code": "courses_5",
        "name": "Explorer",
        "description": "Play 5 different courses.",
        "icon": "🗺️",
        "category": "courses",
        "tier": 1,
        "xp_reward": 100,
        "criteria": {"type": "distinct_courses_played", "count": 5},
    },
    {
        "code": "courses_10",
        "name": "Wanderer",
        "description": "Play 10 different courses.",
        "icon": "🗺️",
        "category": "courses",
        "tier": 2,
        "xp_reward": 200,
        "criteria": {"type": "distinct_courses_played", "count": 10},
    },
    {
        "code": "first_course_created",
        "name": "Course Builder",
        "description": "Add your first course.",
        "icon": "🏗️",
        "category": "courses",
        "tier": 1,
        "xp_reward": 75,
        "criteria": {"type": "courses_created", "count": 1},
    },
    {
        "code": "sub_par_round",
        "name": "Below Par",
        "description": "Complete a round under par.",
        "icon": "📉",
        "category": "scoring",
        "tier": 1,
        "xp_reward": 150,
        "criteria": {"type": "round_score_to_par", "max": -1},
    },
    {
        "code": "three_birdies_in_round",
        "name": "Birdie Streak",
        "description": "Score 3 birdies (or better) in a single round.",
        "icon": "🐦",
        "category": "scoring",
        "tier": 2,
        "xp_reward": 150,
        "criteria": {"type": "birdies_in_single_round", "count": 3},
    },
    {
        "code": "played_every_month",
        "name": "All Year Round",
        "description": "Play at least one round in 12 different calendar months.",
        "icon": "📅",
        "category": "consistency",
        "tier": 2,
        "xp_reward": 300,
        "criteria": {"type": "distinct_months_played", "count": 12},
    },
    {
        "code": "beat_friends_best",
        "name": "Rival",
        "description": "Beat a friend's personal best on a shared layout.",
        "icon": "⚔️",
        "category": "social",
        "tier": 2,
        "xp_reward": 100,
        "criteria": {"type": "beat_friend_personal_best"},
    },
    {
        "code": "streak_7",
        "name": "On a Roll",
        "description": "Play on 7 consecutive days.",
        "icon": "🔥",
        "category": "streaks",
        "tier": 1,
        "xp_reward": 100,
        "criteria": {"type": "play_streak", "days": 7},
    },
    {
        "code": "streak_30",
        "name": "Unstoppable",
        "description": "Play on 30 consecutive days.",
        "icon": "🔥",
        "category": "streaks",
        "tier": 2,
        "xp_reward": 400,
        "criteria": {"type": "play_streak", "days": 30},
    },
]


async def seed() -> None:
    async with async_session_maker() as session:
        for definition in ACHIEVEMENTS:
            existing = await session.execute(
                select(Achievement).where(Achievement.code == definition["code"])
            )
            achievement = existing.scalar_one_or_none()

            if achievement is None:
                session.add(Achievement(id=uuid.uuid4(), **definition))
            else:
                for field, value in definition.items():
                    if field != "code":
                        setattr(achievement, field, value)

        await session.commit()
    print(f"Seeded {len(ACHIEVEMENTS)} achievement definitions")


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
