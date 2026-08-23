import uuid
from typing import Any

from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, **overrides: str) -> dict[str, Any]:
    payload = {
        "email": "stats@example.com",
        "username": "statsuser",
        "display_name": "Stats User",
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


async def _play_round(
    client: AsyncClient,
    headers: dict[str, str],
    user_id: str,
    layout_id: str,
    hole_ids: list[str],
    strokes: list[int],
) -> None:
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
    await client.post(f"/rounds/{round_id}/complete", headers=headers)


async def _setup_known_history(client: AsyncClient) -> dict[str, Any]:
    """Layout: par3, par4, par5. Three completed rounds with known scores:
    round1 = [3,4,5] (all pars, diff 0)
    round2 = [1,3,4] (ace, birdie, birdie, diff -4)
    round3 = [4,5,7] (bogey, bogey, double+, diff +4)
    """
    headers = await _auth_headers(client)
    user_id = await _user_id(client, headers)

    layout_id = str(uuid.uuid4())
    hole1, hole2, hole3 = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    await client.post(
        "/courses",
        headers=headers,
        json={
            "id": str(uuid.uuid4()),
            "name": "Stats Fixture Course",
            "location": {"lat": 59.437, "lng": 24.7536},
            "layouts": [
                {
                    "id": layout_id,
                    "name": "Main",
                    "holes": [
                        {"id": hole1, "number": 1, "par": 3},
                        {"id": hole2, "number": 2, "par": 4},
                        {"id": hole3, "number": 3, "par": 5},
                    ],
                }
            ],
        },
    )

    hole_ids = [hole1, hole2, hole3]
    await _play_round(client, headers, user_id, layout_id, hole_ids, [3, 4, 5])
    await _play_round(client, headers, user_id, layout_id, hole_ids, [1, 3, 4])
    await _play_round(client, headers, user_id, layout_id, hole_ids, [4, 5, 7])

    return {
        "headers": headers,
        "user_id": user_id,
        "layout_id": layout_id,
        "hole1": hole1,
        "hole2": hole2,
        "hole3": hole3,
    }


async def test_summary_reflects_known_round_history(db_client: AsyncClient) -> None:
    fixture = await _setup_known_history(db_client)

    response = await db_client.get("/stats/me/summary", headers=fixture["headers"])

    assert response.status_code == 200
    body = response.json()
    assert body["rounds_played"] == 3
    assert body["courses_played"] == 1
    assert body["layouts_played"] == 1
    assert body["avg_score_to_par"] == 0.0
    assert body["best_round"]["score_to_par"] == -4
    assert body["total_holes_played"] == 9
    assert body["score_distribution"] == {
        "ace": 1,
        "eagle": 0,
        "birdie": 2,
        "par": 3,
        "bogey": 2,
        "double_bogey_or_worse": 1,
    }


async def test_layout_stats_reflects_known_round_history(db_client: AsyncClient) -> None:
    fixture = await _setup_known_history(db_client)

    response = await db_client.get(
        f"/stats/me/layouts/{fixture['layout_id']}", headers=fixture["headers"]
    )

    assert response.status_code == 200
    body = response.json()
    assert body["rounds_played"] == 3
    assert body["best_score_to_par"] == -4
    assert body["average_score_to_par"] == 0.0
    assert len(body["trend"]) == 3
    assert len(body["hole_averages"]) == 3
    hole1_avg = next(h for h in body["hole_averages"] if h["hole_number"] == 1)
    assert hole1_avg["average_strokes"] == (3 + 1 + 4) / 3
    assert hole1_avg["attempts"] == 3


async def test_layout_stats_404_for_unknown_layout(db_client: AsyncClient) -> None:
    headers = await _auth_headers(db_client)

    response = await db_client.get(f"/stats/me/layouts/{uuid.uuid4()}", headers=headers)

    assert response.status_code == 404


async def test_hole_stats_reflects_known_round_history(db_client: AsyncClient) -> None:
    fixture = await _setup_known_history(db_client)

    response = await db_client.get(
        f"/stats/me/holes/{fixture['hole1']}", headers=fixture["headers"]
    )

    assert response.status_code == 200
    body = response.json()
    assert body["attempts"] == 3
    assert body["best_strokes"] == 1
    assert body["average_strokes"] == (3 + 1 + 4) / 3
    assert body["score_distribution"] == {
        "ace": 1,
        "eagle": 0,
        "birdie": 0,
        "par": 1,
        "bogey": 1,
        "double_bogey_or_worse": 0,
    }


async def test_hole_stats_404_for_unknown_hole(db_client: AsyncClient) -> None:
    headers = await _auth_headers(db_client)

    response = await db_client.get(f"/stats/me/holes/{uuid.uuid4()}", headers=headers)

    assert response.status_code == 404


async def test_trend_groups_rounds_by_period(db_client: AsyncClient) -> None:
    fixture = await _setup_known_history(db_client)

    response = await db_client.get(
        "/stats/me/trend", headers=fixture["headers"], params={"period": "month"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["period"] == "month"
    assert len(body["points"]) == 1
    point = body["points"][0]
    assert point["rounds_played"] == 3
    assert point["avg_score_to_par"] == 0.0


async def test_trend_rejects_invalid_period(db_client: AsyncClient) -> None:
    headers = await _auth_headers(db_client)

    response = await db_client.get(
        "/stats/me/trend", headers=headers, params={"period": "decade"}
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_period"
