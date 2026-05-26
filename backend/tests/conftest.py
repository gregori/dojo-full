"""Test fixtures for backend tests."""

import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.api.dependencies.get_db import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token_raw,
    hash_password,
)
from app.database import Base
from app.domain.models.org import Org
from app.domain.models.user import User
from app.main import app

# Use a test database URL (can be overridden via env vars)
TEST_DATABASE_URL = "mysql+aiomysql://root:@localhost:3306/dojo_test"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def setup_database():
    """Create all tables before tests and drop them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(setup_database) -> AsyncGenerator[AsyncSession]:
    """Provide a test database session with rollback after each test."""
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.rollback()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest_asyncio.fixture
async def async_client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient]:
    """Provide an async HTTP client for testing API endpoints."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def default_org(db_session: AsyncSession) -> Org:
    """Create the default organization for tests."""
    org = Org(
        id="00000000-0000-0000-0000-000000000001",
        name="Default Dojo",
    )
    db_session.add(org)
    await db_session.flush()
    return org


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, default_org: Org) -> User:
    """Create a test user with student role."""
    user = User(
        id=str(uuid.uuid4()),
        org_id=default_org.id,
        email="student@test.com",
        password_hash=hash_password("testpassword123"),
        name="Test Student",
        roles=["student"],
        auth_provider="email",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def instructor_user(db_session: AsyncSession, default_org: Org) -> User:
    """Create a test user with instructor role."""
    user = User(
        id=str(uuid.uuid4()),
        org_id=default_org.id,
        email="instructor@test.com",
        password_hash=hash_password("testpassword123"),
        name="Test Instructor",
        roles=["instructor", "student"],
        auth_provider="email",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession, default_org: Org) -> User:
    """Create a test user with super-admin role."""
    user = User(
        id=str(uuid.uuid4()),
        org_id=default_org.id,
        email="admin@test.com",
        password_hash=hash_password("testpassword123"),
        name="Test Admin",
        roles=["super-admin"],
        auth_provider="email",
    )
    db_session.add(user)
    await db_session.flush()
    return user


def get_auth_cookies(user: User) -> dict:
    """Generate auth cookies for a given user."""
    token_data = {
        "sub": user.id,
        "email": user.email,
        "roles": user.roles,
        "org_id": user.org_id,
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token_raw()
    return {"access_token": access_token, "refresh_token": refresh_token}
