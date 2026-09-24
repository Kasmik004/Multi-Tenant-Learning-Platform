import os

# Point the app at a dedicated test database before any app module reads settings.
os.environ["POSTGRES_DB"] = os.environ.get("POSTGRES_TEST_DB", "learning_platform_test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-at-least-32-bytes-long")

from collections.abc import AsyncIterator, Awaitable, Callable  # noqa: E402

import asyncpg  # noqa: E402
import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402

API = settings.API_V1_PREFIX
AuthHeaders = dict[str, str]


async def _ensure_test_database() -> None:
    conn = await asyncpg.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database="postgres",
    )
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", settings.POSTGRES_DB
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{settings.POSTGRES_DB}"')
    finally:
        await conn.close()


@pytest.fixture(scope="session", autouse=True)
async def _database() -> AsyncIterator[None]:
    await _ensure_test_database()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest.fixture(autouse=True)
async def _clean_tables() -> AsyncIterator[None]:
    yield
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def create_tenant(client: AsyncClient) -> Callable[[str], Awaitable[AuthHeaders]]:
    """Onboards a tenant and returns Authorization headers for its admin."""

    async def _create(slug: str) -> AuthHeaders:
        password = "s3cret-password"
        email = f"admin@{slug}.example.com"
        resp = await client.post(
            f"{API}/tenants",
            json={
                "name": slug.title(),
                "slug": slug,
                "admin": {"email": email, "full_name": "Admin", "password": password},
            },
        )
        assert resp.status_code == 201, resp.text
        return await login(client, slug, email, password)

    return _create


async def login(client: AsyncClient, slug: str, email: str, password: str) -> AuthHeaders:
    resp = await client.post(
        f"{API}/auth/login", json={"tenant_slug": slug, "email": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
