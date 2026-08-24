import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course


async def _register_and_login(client: AsyncClient, **overrides: str) -> dict[str, Any]:
    payload = {
        "email": "sync@example.com",
        "username": "syncuser",
        "display_name": "Sync User",
        "password": "password123",
    }
    payload.update(overrides)
    response = await client.post("/auth/register", json=payload)
    return dict(response.json())


async def _auth_headers(client: AsyncClient, **overrides: str) -> dict[str, str]:
    tokens = await _register_and_login(client, **overrides)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _create_course(client: AsyncClient, headers: dict[str, str], name: str) -> dict[str, Any]:
    response = await client.post(
        "/courses",
        headers=headers,
        json={
            "id": str(uuid.uuid4()),
            "name": name,
            "location": {"lat": 59.4, "lng": 24.7},
            "layouts": [
                {
                    "id": str(uuid.uuid4()),
                    "name": "Main",
                    "holes": [{"id": str(uuid.uuid4()), "number": 1, "par": 3}],
                }
            ],
        },
    )
    return dict(response.json())


def _iso(dt: datetime) -> str:
    return dt.isoformat()


async def _force_course_updated_at(
    db_session: AsyncSession, course_id: str, when: datetime
) -> None:
    # Postgres' now() is frozen for the lifetime of a transaction, and db_client shares one
    # transaction across every request in a test, so rows created moments apart in real time
    # would otherwise get byte-identical updated_at values. Force distinct ones directly.
    await db_session.execute(
        update(Course).where(Course.id == uuid.UUID(course_id)).values(updated_at=when)
    )
    await db_session.flush()


async def test_full_pull_returns_created_course_layout_and_hole(db_client: AsyncClient) -> None:
    headers = await _auth_headers(db_client)
    course = await _create_course(db_client, headers, "Pull Fixture Course")

    response = await db_client.get("/sync/pull", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert any(c["id"] == course["id"] and c["deleted"] is False for c in body["courses"])
    assert any(layout["course_id"] == course["id"] for layout in body["layouts"])
    assert len(body["holes"]) == 1
    assert body["has_more"] is False


async def test_delta_pull_only_returns_changes_since_cursor(
    db_client: AsyncClient, db_session: AsyncSession
) -> None:
    headers = await _auth_headers(db_client)
    course_one = await _create_course(db_client, headers, "Delta Fixture Course One")
    await _force_course_updated_at(db_session, course_one["id"], datetime(2026, 1, 1, tzinfo=UTC))

    cursor_1 = _iso(datetime(2026, 1, 1, 0, 0, 1, tzinfo=UTC))

    course_two = await _create_course(db_client, headers, "Delta Fixture Course Two")
    await _force_course_updated_at(
        db_session, course_two["id"], datetime(2026, 1, 1, 0, 0, 2, tzinfo=UTC)
    )

    delta = await db_client.get("/sync/pull", headers=headers, params={"since": cursor_1})
    delta_body = delta.json()
    assert [c["id"] for c in delta_body["courses"]] == [course_two["id"]]

    cursor_2 = _iso(datetime(2026, 1, 1, 0, 0, 3, tzinfo=UTC))
    steady_state = await db_client.get("/sync/pull", headers=headers, params={"since": cursor_2})
    assert steady_state.json()["courses"] == []


async def test_delta_pull_surfaces_tombstone_after_delete(
    db_client: AsyncClient, db_session: AsyncSession
) -> None:
    headers = await _auth_headers(db_client)
    course = await _create_course(db_client, headers, "Tombstone Fixture Course")
    await _force_course_updated_at(db_session, course["id"], datetime(2026, 1, 1, tzinfo=UTC))

    cursor = _iso(datetime(2026, 1, 1, 0, 0, 1, tzinfo=UTC))

    delete_response = await db_client.delete(f"/courses/{course['id']}", headers=headers)
    assert delete_response.status_code == 204
    await _force_course_updated_at(
        db_session, course["id"], datetime(2026, 1, 1, 0, 0, 2, tzinfo=UTC)
    )

    delta = await db_client.get("/sync/pull", headers=headers, params={"since": cursor})
    delta_body = delta.json()
    assert len(delta_body["courses"]) == 1
    assert delta_body["courses"][0]["id"] == course["id"]
    assert delta_body["courses"][0]["deleted"] is True

    full_pull = await db_client.get("/sync/pull", headers=headers)
    assert course["id"] not in {c["id"] for c in full_pull.json()["courses"]}


async def test_pull_pages_results_and_reports_has_more(
    db_client: AsyncClient, db_session: AsyncSession
) -> None:
    headers = await _auth_headers(db_client)
    base = datetime(2026, 1, 1, tzinfo=UTC)
    for i in range(3):
        course = await _create_course(db_client, headers, f"Page Fixture Course {i}")
        await _force_course_updated_at(db_session, course["id"], base + timedelta(seconds=i))

    page_1 = await db_client.get("/sync/pull", headers=headers, params={"limit": 2})
    page_1_body = page_1.json()
    assert len(page_1_body["courses"]) == 2
    assert page_1_body["has_more"] is True

    page_2 = await db_client.get(
        "/sync/pull", headers=headers, params={"since": page_1_body["next_cursor"], "limit": 2}
    )
    page_2_body = page_2.json()
    assert len(page_2_body["courses"]) == 1
    assert page_2_body["has_more"] is False

    seen_ids = {c["id"] for c in page_1_body["courses"]} | {c["id"] for c in page_2_body["courses"]}
    assert len(seen_ids) == 3


async def test_push_stale_write_is_rejected_and_newer_write_wins(db_client: AsyncClient) -> None:
    headers = await _auth_headers(db_client)
    course = await _create_course(db_client, headers, "Conflict Fixture Course")
    hole_id = course["layouts"][0]["holes"][0]["id"]

    t0 = datetime.now(UTC)
    t_older = t0 - timedelta(seconds=10)
    t_newer = t0 + timedelta(seconds=10)

    accepted = await db_client.post(
        "/sync/push",
        headers=headers,
        json={
            "mutations": [
                {
                    "mutation_id": str(uuid.uuid4()),
                    "entity_type": "hole",
                    "op": "update",
                    "entity_id": hole_id,
                    "updated_at": _iso(t_newer),
                    "data": {"par": 5},
                }
            ]
        },
    )
    assert accepted.json()["results"][0]["accepted"] is True

    stale = await db_client.post(
        "/sync/push",
        headers=headers,
        json={
            "mutations": [
                {
                    "mutation_id": str(uuid.uuid4()),
                    "entity_type": "hole",
                    "op": "update",
                    "entity_id": hole_id,
                    "updated_at": _iso(t_older),
                    "data": {"par": 9},
                }
            ]
        },
    )
    stale_result = stale.json()["results"][0]
    assert stale_result["accepted"] is False
    assert stale_result["reason"] == "conflict_stale_write"

    pull = await db_client.get("/sync/pull", headers=headers)
    hole = next(h for h in pull.json()["holes"] if h["id"] == hole_id)
    assert hole["par"] == 5


async def test_replayed_push_batch_is_a_noop(db_client: AsyncClient) -> None:
    headers = await _auth_headers(db_client)
    course_id = str(uuid.uuid4())
    layout_id = str(uuid.uuid4())
    hole_id = str(uuid.uuid4())

    batch = {
        "mutations": [
            {
                "mutation_id": str(uuid.uuid4()),
                "entity_type": "course",
                "op": "create",
                "entity_id": course_id,
                "updated_at": _iso(datetime.now(UTC)),
                "data": {"name": "Replay Fixture Course", "location": {"lat": 59.4, "lng": 24.7}},
            },
            {
                "mutation_id": str(uuid.uuid4()),
                "entity_type": "layout",
                "op": "create",
                "entity_id": layout_id,
                "updated_at": _iso(datetime.now(UTC)),
                "data": {"course_id": course_id, "name": "Main"},
            },
            {
                "mutation_id": str(uuid.uuid4()),
                "entity_type": "hole",
                "op": "create",
                "entity_id": hole_id,
                "updated_at": _iso(datetime.now(UTC)),
                "data": {"layout_id": layout_id, "number": 1, "par": 3},
            },
        ]
    }

    first = await db_client.post("/sync/push", headers=headers, json=batch)
    assert all(r["accepted"] for r in first.json()["results"])

    replay = await db_client.post("/sync/push", headers=headers, json=batch)
    assert replay.json()["results"] == first.json()["results"]

    pull = await db_client.get("/sync/pull", headers=headers)
    pull_body = pull.json()
    assert [c["id"] for c in pull_body["courses"]] == [course_id]
    assert [layout["id"] for layout in pull_body["layouts"]] == [layout_id]
    assert [hole["id"] for hole in pull_body["holes"]] == [hole_id]
    assert pull_body["layouts"][0]["hole_count"] == 1
    assert pull_body["layouts"][0]["par_total"] == 3


async def test_replayed_rejected_mutation_returns_cached_rejection(db_client: AsyncClient) -> None:
    headers = await _auth_headers(db_client)
    course = await _create_course(db_client, headers, "Replay Rejection Fixture Course")
    hole_id = course["layouts"][0]["holes"][0]["id"]

    stale_batch = {
        "mutations": [
            {
                "mutation_id": str(uuid.uuid4()),
                "entity_type": "hole",
                "op": "update",
                "entity_id": hole_id,
                "updated_at": _iso(datetime.now(UTC) - timedelta(days=1)),
                "data": {"par": 9},
            }
        ]
    }

    first = await db_client.post("/sync/push", headers=headers, json=stale_batch)
    first_result = first.json()["results"][0]
    assert first_result["accepted"] is False

    replay = await db_client.post("/sync/push", headers=headers, json=stale_batch)
    assert replay.json()["results"][0] == first_result

    pull = await db_client.get("/sync/pull", headers=headers)
    hole = next(h for h in pull.json()["holes"] if h["id"] == hole_id)
    assert hole["par"] == 3
