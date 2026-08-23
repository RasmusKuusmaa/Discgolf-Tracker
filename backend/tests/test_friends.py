import uuid
from typing import Any

from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, **overrides: str) -> dict[str, Any]:
    payload = {
        "email": "friends@example.com",
        "username": "friendsuser",
        "display_name": "Friends User",
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


async def _befriend(
    client: AsyncClient,
    a_headers: dict[str, str],
    b_headers: dict[str, str],
    b_username: str,
) -> None:
    req = await client.post("/friends/requests", headers=a_headers, json={"username": b_username})
    await client.post(f"/friends/requests/{req.json()['id']}/accept", headers=b_headers)


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
            "name": "Friends Test Course",
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


async def _play_completed_round(
    client: AsyncClient,
    headers: dict[str, str],
    user_id: str,
    layout_id: str,
    hole_id: str,
    strokes: int,
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
                    "strokes": strokes,
                }
            ]
        },
    )
    await client.post(f"/rounds/{round_id}/complete", headers=headers)


async def test_friend_request_lifecycle(db_client: AsyncClient) -> None:
    alice_headers = await _auth_headers(db_client, email="alice@example.com", username="alice")
    bob_headers = await _auth_headers(db_client, email="bob@example.com", username="bob")
    bob_id = await _user_id(db_client, bob_headers)

    req = await db_client.post(
        "/friends/requests", headers=alice_headers, json={"username": "bob"}
    )
    assert req.status_code == 201
    request_id = req.json()["id"]

    dup = await db_client.post(
        "/friends/requests", headers=alice_headers, json={"username": "bob"}
    )
    assert dup.status_code == 409
    assert dup.json()["code"] == "request_already_pending"

    wrong_accept = await db_client.post(
        f"/friends/requests/{request_id}/accept", headers=alice_headers
    )
    assert wrong_accept.status_code == 403

    accept = await db_client.post(
        f"/friends/requests/{request_id}/accept", headers=bob_headers
    )
    assert accept.status_code == 200
    assert accept.json()["status"] == "accepted"

    friends_list = await db_client.get("/friends", headers=alice_headers)
    assert [f["user"]["username"] for f in friends_list.json()["items"]] == ["bob"]

    already = await db_client.post(
        "/friends/requests", headers=alice_headers, json={"username": "bob"}
    )
    assert already.status_code == 409
    assert already.json()["code"] == "already_friends"

    unfriend = await db_client.delete(f"/friends/{bob_id}", headers=alice_headers)
    assert unfriend.status_code == 204

    re_request = await db_client.post(
        "/friends/requests", headers=alice_headers, json={"username": "bob"}
    )
    assert re_request.status_code == 201

    decline = await db_client.post(
        f"/friends/requests/{re_request.json()['id']}/decline", headers=bob_headers
    )
    assert decline.status_code == 204

    re_request_after_decline = await db_client.post(
        "/friends/requests", headers=alice_headers, json={"username": "bob"}
    )
    assert re_request_after_decline.status_code == 201


async def test_blocking_prevents_requests_and_hides_profile(db_client: AsyncClient) -> None:
    blocker_headers = await _auth_headers(
        db_client, email="blocker@example.com", username="blocker"
    )
    blocked_headers = await _auth_headers(
        db_client, email="blocked@example.com", username="blockeduser"
    )
    blocked_id = await _user_id(db_client, blocked_headers)

    block = await db_client.post(f"/friends/block/{blocked_id}", headers=blocker_headers)
    assert block.status_code == 200
    assert block.json()["status"] == "blocked"

    from_blocked = await db_client.post(
        "/friends/requests", headers=blocked_headers, json={"username": "blocker"}
    )
    assert from_blocked.status_code == 403
    assert from_blocked.json()["code"] == "blocked"

    from_blocker = await db_client.post(
        "/friends/requests", headers=blocker_headers, json={"username": "blockeduser"}
    )
    assert from_blocker.status_code == 403

    hidden = await db_client.get("/users/blockeduser", headers=blocker_headers)
    assert hidden.status_code == 404

    unblock = await db_client.post(f"/friends/unblock/{blocked_id}", headers=blocker_headers)
    assert unblock.status_code == 204

    visible_again = await db_client.get("/users/blockeduser", headers=blocker_headers)
    assert visible_again.status_code == 200


async def test_feed_respects_stats_visibility(db_client: AsyncClient) -> None:
    viewer_headers = await _auth_headers(db_client, email="viewer@example.com", username="viewer")

    public_friend_headers = await _auth_headers(
        db_client, email="publicfriend@example.com", username="publicfriend"
    )
    public_friend_id = await _user_id(db_client, public_friend_headers)

    private_friend_headers = await _auth_headers(
        db_client, email="privatefriend@example.com", username="privatefriend"
    )
    private_friend_id = await _user_id(db_client, private_friend_headers)
    await db_client.patch(
        "/users/me", headers=private_friend_headers, json={"stats_visibility": "private"}
    )

    await _befriend(db_client, viewer_headers, public_friend_headers, "publicfriend")
    await _befriend(db_client, viewer_headers, private_friend_headers, "privatefriend")

    layout_id, (hole_id, _hole2) = await _create_layout_with_holes(db_client, viewer_headers)

    await _play_completed_round(
        db_client, public_friend_headers, public_friend_id, layout_id, hole_id, 3
    )
    await _play_completed_round(
        db_client, private_friend_headers, private_friend_id, layout_id, hole_id, 1
    )

    feed = await db_client.get("/feed", headers=viewer_headers)
    assert feed.status_code == 200
    usernames = [item["user"]["username"] for item in feed.json()["items"]]
    assert usernames == ["publicfriend"]


async def test_comparison_requires_friendship(db_client: AsyncClient) -> None:
    viewer_headers = await _auth_headers(db_client, email="cviewer@example.com", username="cviewer")
    stranger_headers = await _auth_headers(
        db_client, email="cstranger@example.com", username="cstranger"
    )
    stranger_id = await _user_id(db_client, stranger_headers)

    response = await db_client.get(
        f"/friends/{stranger_id}/comparison",
        headers=viewer_headers,
        params={"layout_id": str(uuid.uuid4())},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "not_friends"


async def test_comparison_with_no_shared_layout_history(db_client: AsyncClient) -> None:
    a_headers = await _auth_headers(db_client, email="cmpa@example.com", username="cmpa")
    b_headers = await _auth_headers(db_client, email="cmpb@example.com", username="cmpb")
    b_id = await _user_id(db_client, b_headers)

    await _befriend(db_client, a_headers, b_headers, "cmpb")
    layout_id, _holes = await _create_layout_with_holes(db_client, a_headers)

    response = await db_client.get(
        f"/friends/{b_id}/comparison", headers=a_headers, params={"layout_id": layout_id}
    )
    assert response.status_code == 422
    assert response.json()["code"] == "no_shared_history"


async def test_comparison_returns_hole_by_hole_results(db_client: AsyncClient) -> None:
    a_headers = await _auth_headers(db_client, email="cmpc@example.com", username="cmpc")
    a_id = await _user_id(db_client, a_headers)
    b_headers = await _auth_headers(db_client, email="cmpd@example.com", username="cmpd")
    b_id = await _user_id(db_client, b_headers)

    await _befriend(db_client, a_headers, b_headers, "cmpd")
    layout_id, (hole1, hole2) = await _create_layout_with_holes(db_client, a_headers)

    async def play(headers: dict[str, str], user_id: str, s1: int, s2: int) -> None:
        player_id = str(uuid.uuid4())
        round_id = str(uuid.uuid4())
        await db_client.post(
            "/rounds",
            headers=headers,
            json={
                "id": round_id,
                "layout_id": layout_id,
                "players": [{"id": player_id, "user_id": user_id, "position": 1}],
            },
        )
        await db_client.put(
            f"/rounds/{round_id}/scores",
            headers=headers,
            json={
                "scores": [
                    {"id": str(uuid.uuid4()), "round_player_id": player_id, "hole_id": hole1,
                     "strokes": s1},
                    {"id": str(uuid.uuid4()), "round_player_id": player_id, "hole_id": hole2,
                     "strokes": s2},
                ]
            },
        )
        await db_client.post(f"/rounds/{round_id}/complete", headers=headers)

    await play(a_headers, a_id, 2, 5)
    await play(b_headers, b_id, 3, 4)

    response = await db_client.get(
        f"/friends/{b_id}/comparison", headers=a_headers, params={"layout_id": layout_id}
    )
    assert response.status_code == 200
    body = response.json()
    results = {h["hole_number"]: h["result"] for h in body["holes"]}
    assert results[1] == "win"
    assert results[2] == "loss"
