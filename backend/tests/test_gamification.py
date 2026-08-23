import uuid
from datetime import date
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.achievements import AchievementProgress
from app.core.gamification import _apply_achievement_progress, get_total_xp, update_play_streak
from app.core.leveling import level_for_xp, xp_for_level, xp_to_next_level
from app.models.achievement import Achievement
from app.models.user import User
from app.models.user_achievement import UserAchievement


async def _make_user(db_session: AsyncSession) -> uuid.UUID:
    user = User(
        email=f"{uuid.uuid4()}@example.com",
        username=f"user{uuid.uuid4().hex[:12]}",
        display_name="Fixture User",
        password_hash="unused",
    )
    db_session.add(user)
    await db_session.flush()
    return user.id


def test_level_for_xp_thresholds() -> None:
    assert level_for_xp(0) == 1
    assert level_for_xp(99) == 1
    assert level_for_xp(100) == 2
    assert level_for_xp(399) == 2
    assert level_for_xp(400) == 3
    assert level_for_xp(899) == 3
    assert level_for_xp(900) == 4


def test_xp_for_level_round_trips_with_level_for_xp() -> None:
    for level in range(1, 10):
        threshold = xp_for_level(level)
        assert level_for_xp(threshold) == level
        if threshold > 0:
            assert level_for_xp(threshold - 1) == level - 1


def test_xp_to_next_level_counts_down_to_next_threshold() -> None:
    assert xp_to_next_level(0) == 100
    assert xp_to_next_level(99) == 1
    assert xp_to_next_level(100) == 300
    assert xp_to_next_level(399) == 1


async def test_update_play_streak_increments_on_consecutive_days(
    db_session: AsyncSession,
) -> None:
    user_id = await _make_user(db_session)

    streak = await update_play_streak(db_session, user_id, date(2026, 1, 1))
    assert (streak.current_streak, streak.longest_streak) == (1, 1)

    streak = await update_play_streak(db_session, user_id, date(2026, 1, 2))
    assert (streak.current_streak, streak.longest_streak) == (2, 2)

    streak = await update_play_streak(db_session, user_id, date(2026, 1, 3))
    assert (streak.current_streak, streak.longest_streak) == (3, 3)


async def test_update_play_streak_same_day_is_idempotent(db_session: AsyncSession) -> None:
    user_id = await _make_user(db_session)

    await update_play_streak(db_session, user_id, date(2026, 1, 1))
    streak = await update_play_streak(db_session, user_id, date(2026, 1, 1))

    assert (streak.current_streak, streak.longest_streak) == (1, 1)


async def test_update_play_streak_resets_on_gap_but_keeps_longest(
    db_session: AsyncSession,
) -> None:
    user_id = await _make_user(db_session)

    await update_play_streak(db_session, user_id, date(2026, 1, 1))
    await update_play_streak(db_session, user_id, date(2026, 1, 2))
    await update_play_streak(db_session, user_id, date(2026, 1, 3))

    streak = await update_play_streak(db_session, user_id, date(2026, 1, 10))

    assert streak.current_streak == 1
    assert streak.longest_streak == 3
    assert streak.last_played_date == date(2026, 1, 10)


async def test_update_play_streak_sets_new_longest_after_recovering_from_gap(
    db_session: AsyncSession,
) -> None:
    user_id = await _make_user(db_session)

    await update_play_streak(db_session, user_id, date(2026, 1, 1))
    await update_play_streak(db_session, user_id, date(2026, 1, 2))
    await update_play_streak(db_session, user_id, date(2026, 1, 10))
    await update_play_streak(db_session, user_id, date(2026, 1, 11))
    await update_play_streak(db_session, user_id, date(2026, 1, 12))
    streak = await update_play_streak(db_session, user_id, date(2026, 1, 13))

    assert streak.current_streak == 4
    assert streak.longest_streak == 4


def _make_achievement(
    code: str, criteria: dict[str, Any], xp_reward: int = 25, tier: int = 1
) -> Achievement:
    return Achievement(
        code=code,
        name=code,
        description=code,
        icon="disc",
        category="rounds",
        tier=tier,
        xp_reward=xp_reward,
        criteria=criteria,
    )


async def test_apply_achievement_progress_never_unlocks_twice(db_session: AsyncSession) -> None:
    achievement = _make_achievement("test_first_round", {"type": "rounds_played", "count": 1})
    db_session.add(achievement)
    await db_session.flush()

    user_id = await _make_user(db_session)
    progress = AchievementProgress(achievement=achievement, progress=1.0, unlocked=True)

    first_unlocked = await _apply_achievement_progress(db_session, user_id, [progress])
    assert [a.code for a in first_unlocked] == ["test_first_round"]

    second_unlocked = await _apply_achievement_progress(db_session, user_id, [progress])
    assert second_unlocked == []

    assert await get_total_xp(db_session, user_id) == 25


async def test_apply_achievement_progress_tracks_partial_progress_before_unlock(
    db_session: AsyncSession,
) -> None:
    achievement = _make_achievement(
        "test_ten_rounds", {"type": "rounds_played", "count": 10}, xp_reward=50, tier=2
    )
    db_session.add(achievement)
    await db_session.flush()

    user_id = await _make_user(db_session)

    partial = AchievementProgress(achievement=achievement, progress=0.5, unlocked=False)
    assert await _apply_achievement_progress(db_session, user_id, [partial]) == []

    record = (
        await db_session.execute(
            select(UserAchievement).where(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement.id,
            )
        )
    ).scalar_one()
    assert record.progress == pytest.approx(0.5)
    assert record.unlocked_at is None
    assert await get_total_xp(db_session, user_id) == 0

    full = AchievementProgress(achievement=achievement, progress=1.0, unlocked=True)
    unlocked_now = await _apply_achievement_progress(db_session, user_id, [full])
    assert [a.code for a in unlocked_now] == ["test_ten_rounds"]
    assert await get_total_xp(db_session, user_id) == 50


async def _register_and_login(client: AsyncClient, **overrides: str) -> dict[str, Any]:
    payload = {
        "email": "gamification@example.com",
        "username": "gamificationuser",
        "display_name": "Gamification User",
        "password": "password123",
    }
    payload.update(overrides)
    response = await client.post("/auth/register", json=payload)
    return dict(response.json())


async def _auth_headers(client: AsyncClient, **overrides: str) -> dict[str, str]:
    tokens = await _register_and_login(client, **overrides)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _user_id(client: AsyncClient, headers: dict[str, str]) -> str:
    response = await client.get("/users/me", headers=headers)
    return str(response.json()["id"])


async def _create_layout(client: AsyncClient, headers: dict[str, str]) -> tuple[str, list[str]]:
    layout_id = str(uuid.uuid4())
    hole_ids = [str(uuid.uuid4()) for _ in range(3)]
    await client.post(
        "/courses",
        headers=headers,
        json={
            "id": str(uuid.uuid4()),
            "name": "Gamification Fixture Course",
            "location": {"lat": 59.437, "lng": 24.7536},
            "layouts": [
                {
                    "id": layout_id,
                    "name": "Main",
                    "holes": [
                        {"id": hole_ids[0], "number": 1, "par": 3},
                        {"id": hole_ids[1], "number": 2, "par": 4},
                        {"id": hole_ids[2], "number": 3, "par": 5},
                    ],
                }
            ],
        },
    )
    return layout_id, hole_ids


async def _play_round(
    client: AsyncClient,
    headers: dict[str, str],
    user_id: str,
    layout_id: str,
    hole_ids: list[str],
    strokes: list[int],
) -> dict[str, Any]:
    player_id = str(uuid.uuid4())
    round_id = str(uuid.uuid4())
    await client.post(
        "/rounds",
        headers=headers,
        json={
            "id": round_id,
            "layout_id": layout_id,
            "players": [{"id": player_id, "user_id": user_id, "position": 1}],
        },
    )
    await client.put(
        f"/rounds/{round_id}/scores",
        headers=headers,
        json={
            "scores": [
                {
                    "id": str(uuid.uuid4()),
                    "round_player_id": player_id,
                    "hole_id": hole_id,
                    "strokes": stroke_count,
                }
                for hole_id, stroke_count in zip(hole_ids, strokes, strict=True)
            ]
        },
    )
    response = await client.post(f"/rounds/{round_id}/complete", headers=headers)
    return dict(response.json())


async def test_completing_two_rounds_unlocks_matching_achievement_only_once(
    db_client: AsyncClient, db_session: AsyncSession
) -> None:
    achievement = _make_achievement("test_played_a_round", {"type": "rounds_played", "count": 1})
    db_session.add(achievement)
    await db_session.flush()

    headers = await _auth_headers(db_client)
    user_id = await _user_id(db_client, headers)
    layout_id, hole_ids = await _create_layout(db_client, headers)

    first = await _play_round(db_client, headers, user_id, layout_id, hole_ids, [3, 4, 5])
    assert [a["code"] for a in first["rewards"]["new_achievements"]] == ["test_played_a_round"]

    second = await _play_round(db_client, headers, user_id, layout_id, hole_ids, [3, 4, 5])
    assert second["rewards"]["new_achievements"] == []

    profile = await db_client.get("/gamification/me", headers=headers)
    body = profile.json()
    matching = next(a for a in body["achievements"] if a["code"] == "test_played_a_round")
    assert matching["unlocked"] is True
    assert matching["progress"] == 1.0
