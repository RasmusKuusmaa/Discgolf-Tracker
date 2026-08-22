from httpx import AsyncClient


async def test_health_returns_version_and_db_status(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "0.1.0"
    assert isinstance(body["database_reachable"], bool)
