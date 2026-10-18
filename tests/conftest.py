import os
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.main import app
from app.database import Base, get_db
from app import models  # noqa

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://train:train@localhost:5432/train_management_test")
engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestSession = async_sessionmaker(engine, expire_on_commit=False)

@pytest_asyncio.fixture(autouse=True)
async def reset_db():
    """Recreate the test schema for isolation; requires a dedicated test database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session():
    async with TestSession() as session: yield session

@pytest_asyncio.fixture
async def client():
    async def override_get_db():
        async with TestSession() as session: yield session
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c: yield c
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def seeded(client):
    from app.seed import seed
    await seed()
    return client
