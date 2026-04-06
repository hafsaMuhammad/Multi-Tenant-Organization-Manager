import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from testcontainers.postgres import PostgresContainer

from app.db.session import Base, get_db
from app.main import app



@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
def db_url(postgres_container: PostgresContainer) -> str:
    url = postgres_container.get_connection_url()
    # testcontainers gives psycopg2 URL — switch to asyncpg
    return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine(db_url: str):
    _engine = create_async_engine(db_url, echo=False)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield _engine
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    TestingSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()  


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()



async def register_and_login(client: AsyncClient, email: str, password: str, full_name: str) -> str:
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "full_name": full_name,
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
    })
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient) -> str:
    return await register_and_login(client, "admin@test.com", "AdminPass1", "Admin User")


@pytest_asyncio.fixture
async def member_token(client: AsyncClient) -> str:
    return await register_and_login(client, "member@test.com", "MemberPass1", "Member User")


@pytest_asyncio.fixture
async def org_id(client: AsyncClient, admin_token: str) -> int:
    resp = await client.post(
        "/api/v1/organizations",
        json={"org_name": "Test Org"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    return resp.json()["org_id"]