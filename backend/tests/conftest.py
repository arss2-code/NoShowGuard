import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database import Base, get_db
import app.bot.handlers as bot_handlers
from app.main import app as fastapi_app

TEST_DB_URL = "sqlite+aiosqlite:///./test_noshowguard.db"

test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False}
)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Перенаправляем сессии бота в тестовую базу во время тестов
bot_handlers.AsyncSessionLocal = TestAsyncSessionLocal

@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with TestAsyncSessionLocal() as session:
        yield session

@pytest_asyncio.fixture(scope="function")
async def client():
    async def override_get_db():
        async with TestAsyncSessionLocal() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    fastapi_app.dependency_overrides.clear()
