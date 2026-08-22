from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.session import get_session
from app.main import app

settings = get_settings()
TEST_DATABASE_URL = settings.database_url.rsplit("/", 1)[0] + "/discgolf_test"

test_engine = create_async_engine(TEST_DATABASE_URL)
TestSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """A session bound to a connection whose outer transaction is rolled back
    after the test, so no test can leak data into another."""
    async with test_engine.connect() as connection:
        transaction = await connection.begin()
        session = TestSessionLocal(bind=connection)
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """An AsyncClient whose requests share the rolled-back test transaction."""

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()
