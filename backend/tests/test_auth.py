from typing import Any

from httpx import AsyncClient


async def _register(client: AsyncClient, **overrides: str) -> dict[str, Any]:
    payload = {
        "email": "auth@example.com",
        "username": "authuser",
        "display_name": "Auth User",
        "password": "password123",
    }
    payload.update(overrides)
    response = await client.post("/auth/register", json=payload)
    return response.json() if response.status_code == 201 else {}


async def test_register_returns_token_pair(db_client: AsyncClient) -> None:
    response = await db_client.post(
        "/auth/register",
        json={
            "email": "new@example.com",
            "username": "newuser",
            "display_name": "New User",
            "password": "password123",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


async def test_register_rejects_duplicate_email(db_client: AsyncClient) -> None:
    await _register(db_client)

    response = await db_client.post(
        "/auth/register",
        json={
            "email": "auth@example.com",
            "username": "someoneelse",
            "display_name": "Someone Else",
            "password": "password123",
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == "user_exists"


async def test_login_succeeds_with_correct_credentials(db_client: AsyncClient) -> None:
    await _register(db_client)

    response = await db_client.post(
        "/auth/login", json={"identifier": "authuser", "password": "password123"}
    )

    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_login_fails_with_wrong_password(db_client: AsyncClient) -> None:
    await _register(db_client)

    response = await db_client.post(
        "/auth/login", json={"identifier": "authuser", "password": "wrong-password"}
    )

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"


async def test_refresh_rotates_token_and_detects_reuse(db_client: AsyncClient) -> None:
    tokens = await _register(db_client)
    old_refresh = tokens["refresh_token"]

    first = await db_client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert first.status_code == 200
    new_refresh = first.json()["refresh_token"]
    assert new_refresh != old_refresh

    reuse = await db_client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse.status_code == 401
    assert reuse.json()["code"] == "token_reuse_detected"

    also_revoked = await db_client.post("/auth/refresh", json={"refresh_token": new_refresh})
    assert also_revoked.status_code == 401
    assert also_revoked.json()["code"] == "token_reuse_detected"


async def test_protected_route_requires_token(db_client: AsyncClient) -> None:
    response = await db_client.get("/users/me")

    assert response.status_code == 401
