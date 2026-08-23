import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course, CourseStatus


async def _register_and_login(client: AsyncClient, **overrides: str) -> dict[str, Any]:
    payload = {
        "email": "courses@example.com",
        "username": "coursesuser",
        "display_name": "Courses User",
        "password": "password123",
    }
    payload.update(overrides)
    response = await client.post("/auth/register", json=payload)
    return dict(response.json())


async def _auth_headers(client: AsyncClient, **overrides: str) -> dict[str, str]:
    tokens = await _register_and_login(client, **overrides)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _course_payload(
    name: str = "Test Course",
    lat: float = 59.437,
    lng: float = 24.7536,
    **overrides: Any,
) -> dict[str, Any]:
    payload = {
        "id": str(uuid.uuid4()),
        "name": name,
        "location": {"lat": lat, "lng": lng},
        "layouts": [
            {
                "id": str(uuid.uuid4()),
                "name": "Main",
                "holes": [
                    {"id": str(uuid.uuid4()), "number": 1, "par": 3, "distance_m": 90.0},
                    {"id": str(uuid.uuid4()), "number": 2, "par": 4},
                ],
            }
        ],
    }
    payload.update(overrides)
    return payload


async def test_create_course_with_layout_and_holes(db_client: AsyncClient) -> None:
    headers = await _auth_headers(db_client)

    response = await db_client.post("/courses", headers=headers, json=_course_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Test Course"
    layout = body["layouts"][0]
    assert layout["hole_count"] == 2
    assert layout["par_total"] == 7
    holes = {hole["number"]: hole for hole in layout["holes"]}
    assert holes[1]["distance_m"] == 90.0
    assert holes[2]["distance_m"] is None


async def test_nearby_search_returns_only_courses_within_radius(db_client: AsyncClient) -> None:
    headers = await _auth_headers(db_client)

    near = await db_client.post(
        "/courses",
        headers=headers,
        json=_course_payload(name="Nearby Course", lat=59.44, lng=24.75),
    )
    await db_client.post(
        "/courses", headers=headers, json=_course_payload(name="Distant Course", lat=61.0, lng=25.0)
    )
    assert near.status_code == 201

    response = await db_client.get(
        "/courses/nearby", params={"lat": 59.437, "lng": 24.753, "radius_km": 50}
    )

    assert response.status_code == 200
    names = [item["name"] for item in response.json()["items"]]
    assert names == ["Nearby Course"]
    assert response.json()["items"][0]["distance_m"] > 0


async def test_bbox_query_returns_courses_in_viewport(db_client: AsyncClient) -> None:
    headers = await _auth_headers(db_client)

    await db_client.post(
        "/courses",
        headers=headers,
        json=_course_payload(name="Inside Course", lat=59.44, lng=24.75),
    )
    await db_client.post(
        "/courses", headers=headers, json=_course_payload(name="Outside Course", lat=61.0, lng=25.0)
    )

    response = await db_client.get(
        "/courses/bbox",
        params={"min_lat": 59.0, "min_lng": 24.0, "max_lat": 60.0, "max_lng": 25.5},
    )

    assert response.status_code == 200
    names = [item["name"] for item in response.json()["items"]]
    assert names == ["Inside Course"]


async def test_bbox_query_rejects_inverted_bounds(db_client: AsyncClient) -> None:
    response = await db_client.get(
        "/courses/bbox",
        params={"min_lat": 60.0, "min_lng": 24.0, "max_lat": 59.0, "max_lng": 25.5},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_bbox"


async def test_update_and_delete_require_ownership(db_client: AsyncClient) -> None:
    owner_headers = await _auth_headers(db_client, email="owner@example.com", username="owneruser")
    other_headers = await _auth_headers(db_client, email="other@example.com", username="otheruser")

    create = await db_client.post("/courses", headers=owner_headers, json=_course_payload())
    course_id = create.json()["id"]

    forbidden_patch = await db_client.patch(
        f"/courses/{course_id}", headers=other_headers, json={"name": "Hacked"}
    )
    assert forbidden_patch.status_code == 403

    ok_patch = await db_client.patch(
        f"/courses/{course_id}", headers=owner_headers, json={"name": "Renamed"}
    )
    assert ok_patch.status_code == 200
    assert ok_patch.json()["name"] == "Renamed"

    forbidden_delete = await db_client.delete(f"/courses/{course_id}", headers=other_headers)
    assert forbidden_delete.status_code == 403

    ok_delete = await db_client.delete(f"/courses/{course_id}", headers=owner_headers)
    assert ok_delete.status_code == 204

    gone = await db_client.get(f"/courses/{course_id}")
    assert gone.status_code == 404


async def test_create_course_warns_about_nearby_duplicate(
    db_client: AsyncClient, db_session: AsyncSession
) -> None:
    headers = await _auth_headers(db_client)

    first = await db_client.post(
        "/courses",
        headers=headers,
        json=_course_payload(name="Riverside Disc Golf Course", lat=59.437, lng=24.7536),
    )
    first_id = first.json()["id"]

    course = (
        await db_session.execute(select(Course).where(Course.id == uuid.UUID(first_id)))
    ).scalar_one()
    course.status = CourseStatus.PUBLISHED
    await db_session.commit()

    similar_nearby = await db_client.post(
        "/courses",
        headers=headers,
        json=_course_payload(name="Riverside Disc Golf", lat=59.4372, lng=24.7538),
    )
    duplicate_names = [d["name"] for d in similar_nearby.json()["possible_duplicates"]]
    assert duplicate_names == ["Riverside Disc Golf Course"]

    different_name_nearby = await db_client.post(
        "/courses",
        headers=headers,
        json=_course_payload(name="Sunset Park DGC", lat=59.4372, lng=24.7538),
    )
    assert different_name_nearby.json()["possible_duplicates"] == []
