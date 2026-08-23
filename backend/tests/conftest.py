from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.session import get_session
from app.main import app

settings = get_settings()
TEST_DATABASE_URL = settings.database_url.rsplit("/", 1)[0] + "/discgolf_test"


@pytest.fixture(autouse=True)
def _reset_rate_limits() -> None:
    """Rate limit state is global to the app, not per-test — reset it so one
    test's requests can't exhaust another test's quota."""
    limiter.reset()


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """A session bound to a connection whose outer transaction is rolled back
    after the test, so no test can leak data into another.

    The engine is created fresh per test (not at module scope) because
    pytest-asyncio gives each test its own event loop, and an asyncpg
    connection pool cannot be reused across loops.
    """
    test_engine = create_async_engine(TEST_DATABASE_URL)
    test_session_local = async_sessionmaker(bind=test_engine, expire_on_commit=False)
    try:
        async with test_engine.connect() as connection:
            transaction = await connection.begin()
            session = test_session_local(bind=connection)
            try:
                yield session
            finally:
                await session.close()
                await transaction.rollback()
    finally:
        await test_engine.dispose()


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
