import uuid
from typing import Any

from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, **overrides: str) -> dict[str, Any]:
    payload = {
        "email": "rounds@example.com",
        "username": "roundsuser",
        "display_name": "Rounds User",
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


async def _create_layout_with_holes(
    client: AsyncClient, headers: dict[str, str], hole_count: int = 2
) -> tuple[str, list[str]]:
    layout_id = str(uuid.uuid4())
    hole_ids = [str(uuid.uuid4()) for _ in range(hole_count)]
    await client.post(
        "/courses",
        headers=headers,
        json={
            "id": str(uuid.uuid4()),
            "name": "Round Test Course",
            "location": {"lat": 59.437, "lng": 24.7536},
            "layouts": [
                {
                    "id": layout_id,
                    "name": "Main",
                    "holes": [
                        {"id": hole_id, "number": i + 1, "par": 3}
                        for i, hole_id in enumerate(hole_ids)
                    ],
                }
            ],
        },
    )
    return layout_id, hole_ids


async def test_full_round_lifecycle_completes_without_partial(db_client: AsyncClient) -> None:
    headers = await _auth_headers(db_client)
    layout_id, (hole1, hole2) = await _create_layout_with_holes(db_client, headers)

    player_id = str(uuid.uuid4())
    round_id = str(uuid.uuid4())
    create = await db_client.post(
        "/rounds",
        headers=headers,
        json={
            "id": round_id,
            "layout_id": layout_id,
            "players": [{"id": player_id, "guest_name": "Guest", "position": 1}],
        },
    )
    assert create.status_code == 201
    assert create.json()["status"] == "in_progress"

    scores = await db_client.put(
        f"/rounds/{round_id}/scores",
        headers=headers,
        json={
            "scores": [
                {"id": str(uuid.uuid4()), "round_player_id": player_id, "hole_id": hole1,
                 "strokes": 3},
                {"id": str(uuid.uuid4()), "round_player_id": player_id, "hole_id": hole2,
                 "strokes": 4},
            ]
        },
    )
    assert scores.status_code == 200

    complete = await db_client.post(f"/rounds/{round_id}/complete", headers=headers)
    assert complete.status_code == 200
    body = complete.json()
    assert body["status"] == "completed"
    assert body["is_partial"] is False
    assert body["completed_at"] is not None

    detail = await db_client.get(f"/rounds/{round_id}", headers=headers)
    player = detail.json()["players"][0]
    assert player["total_strokes"] == 7
    assert player["score_to_par"] == 1


async def test_partial_round_marks_is_partial_true(db_client: AsyncClient) -> None:
    headers = await _auth_headers(db_client)
    layout_id, (hole1, _hole2) = await _create_layout_with_holes(db_client, headers)

    player_id = str(uuid.uuid4())
    round_id = str(uuid.uuid4())
    await db_client.post(
        "/rounds",
        headers=headers,
        json={
            "id": round_id,
            "layout_id": layout_id,
            "players": [{"id": player_id, "guest_name": "Guest", "position": 1}],
        },
    )
    await db_client.put(
        f"/rounds/{round_id}/scores",
        headers=headers,
        json={
            "scores": [
                {"id": str(uuid.uuid4()), "round_player_id": player_id, "hole_id": hole1,
                 "strokes": 3},
            ]
        },
    )

    complete = await db_client.post(f"/rounds/{round_id}/complete", headers=headers)
    assert complete.status_code == 200
    assert complete.json()["status"] == "completed"
    assert complete.json()["is_partial"] is True


async def test_round_supports_registered_and_guest_players(db_client: AsyncClient) -> None:
    owner_headers = await _auth_headers(db_client, email="owner@example.com", username="owneruser")
    friend_headers = await _auth_headers(
        db_client, email="friend@example.com", username="frienduser"
    )
    owner_id = await _user_id(db_client, owner_headers)
    friend_id = await _user_id(db_client, friend_headers)

    layout_id, _holes = await _create_layout_with_holes(db_client, owner_headers)

    round_id = str(uuid.uuid4())
    response = await db_client.post(
        "/rounds",
        headers=owner_headers,
        json={
            "id": round_id,
            "layout_id": layout_id,
            "players": [
                {"id": str(uuid.uuid4()), "user_id": owner_id, "position": 1},
                {"id": str(uuid.uuid4()), "user_id": friend_id, "position": 2},
                {"id": str(uuid.uuid4()), "guest_name": "Guest Bob", "position": 3},
            ],
        },
    )

    assert response.status_code == 201
    players = response.json()["players"]
    assert {p["user_id"] for p in players if p["user_id"]} == {owner_id, friend_id}
    guest = next(p for p in players if p["guest_name"] is not None)
    assert guest["guest_name"] == "Guest Bob"
    assert guest["user_id"] is None


async def test_scores_are_immutable_after_completion(db_client: AsyncClient) -> None:
    headers = await _auth_headers(db_client)
    layout_id, (hole1, _hole2) = await _create_layout_with_holes(db_client, headers)

    player_id = str(uuid.uuid4())
    round_id = str(uuid.uuid4())
    await db_client.post(
        "/rounds",
        headers=headers,
        json={
            "id": round_id,
            "layout_id": layout_id,
            "players": [{"id": player_id, "guest_name": "Guest", "position": 1}],
        },
    )
    score_payload = {
        "scores": [
            {"id": str(uuid.uuid4()), "round_player_id": player_id, "hole_id": hole1,
             "strokes": 3},
        ]
    }
    await db_client.put(f"/rounds/{round_id}/scores", headers=headers, json=score_payload)
    await db_client.post(f"/rounds/{round_id}/complete", headers=headers)

    blocked = await db_client.put(
        f"/rounds/{round_id}/scores", headers=headers, json=score_payload
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "round_not_in_progress"


async def test_score_upsert_is_idempotent_by_natural_key(db_client: AsyncClient) -> None:
    headers = await _auth_headers(db_client)
    layout_id, (hole1, _hole2) = await _create_layout_with_holes(db_client, headers)

    player_id = str(uuid.uuid4())
    round_id = str(uuid.uuid4())
    await db_client.post(
        "/rounds",
        headers=headers,
        json={
            "id": round_id,
            "layout_id": layout_id,
            "players": [{"id": player_id, "guest_name": "Guest", "position": 1}],
        },
    )

    first = await db_client.put(
        f"/rounds/{round_id}/scores",
        headers=headers,
        json={
            "scores": [
                {"id": str(uuid.uuid4()), "round_player_id": player_id, "hole_id": hole1,
                 "strokes": 3},
            ]
        },
    )
    assert len(first.json()["scores"]) == 1
    original_id = first.json()["scores"][0]["id"]

    retry = await db_client.put(
        f"/rounds/{round_id}/scores",
        headers=headers,
        json={
            "scores": [
                {"id": str(uuid.uuid4()), "round_player_id": player_id, "hole_id": hole1,
                 "strokes": 5},
            ]
        },
    )

    assert len(retry.json()["scores"]) == 1
    assert retry.json()["scores"][0]["id"] == original_id
    assert retry.json()["scores"][0]["strokes"] == 5
