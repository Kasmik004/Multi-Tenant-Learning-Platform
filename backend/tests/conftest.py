import os

# Point the app at a dedicated test database before any app module reads settings.
os.environ["POSTGRES_DB"] = os.environ.get("POSTGRES_TEST_DB", "learning_platform_test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-at-least-32-bytes-long")

from collections.abc import AsyncIterator, Awaitable, Callable  # noqa: E402
from datetime import datetime  # noqa: E402
from typing import Any  # noqa: E402

import asyncpg  # noqa: E402
import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient, Response  # noqa: E402
from sqlalchemy import text, update  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base, PlatformRole, Tenant, User  # noqa: E402
from app.repositories import UserRepository  # noqa: E402

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
        # Reset the whole schema (not drop_all): tables of since-removed models would linger.
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
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


PASSWORD = "s3cret-password"


async def login(
    client: AsyncClient, email: str, password: str = PASSWORD, tenant: str | None = None
) -> AuthHeaders:
    """Returns auth headers; with `tenant`, also scoped to it via X-Tenant-Slug."""
    resp = await client.post(
        f"{API}/auth/login", json={"email": email, "password": password, "tenant_slug": tenant}
    )
    assert resp.status_code == 200, resp.text
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    return in_tenant(headers, tenant) if tenant else headers


def in_tenant(headers: AuthHeaders, slug: str) -> AuthHeaders:
    """Same caller, sending a different X-Tenant-Slug."""
    return {**headers, "X-Tenant-Slug": slug}


async def create_platform_user(client: AsyncClient, email: str, role: PlatformRole) -> AuthHeaders:
    """Platform roles can't be granted over HTTP, so seed them straight into the DB."""
    async with SessionLocal() as session:
        user = User(email=email, hashed_password=hash_password(PASSWORD), platform_role=role)
        await UserRepository(session).add(user)
        await session.commit()
    return await login(client, email)


async def set_trial_end(slug: str, when: datetime) -> None:
    """Moves a tenant's trial end (e.g. into the past) without waiting for real time to pass."""
    async with SessionLocal() as session:
        await session.execute(update(Tenant).where(Tenant.slug == slug).values(trial_ends_at=when))
        await session.commit()


@pytest.fixture
async def superadmin(client: AsyncClient) -> AuthHeaders:
    return await create_platform_user(client, "root@platform.example.com", PlatformRole.SUPERADMIN)


async def send_invite(
    client: AsyncClient, inviter: AuthHeaders, email: str, role: str = "user"
) -> dict[str, Any]:
    """inviter must carry X-Tenant-Slug; returns the invite response body."""
    resp = await client.post(
        f"{API}/users/invites", headers=inviter, json={"email": email, "role": role}
    )
    assert resp.status_code == 201, resp.text
    body: dict[str, Any] = resp.json()
    return body


async def accept_invite(client: AsyncClient, token: str, password: str = PASSWORD) -> Response:
    return await client.post(
        f"{API}/auth/accept-invite",
        json={"token": token, "password": password, "confirm_password": password},
    )


async def invite_user(
    client: AsyncClient, inviter: AuthHeaders, email: str, role: str = "user"
) -> AuthHeaders:
    """Invite + accept end to end; returns the new user's headers in the inviter's tenant."""
    invite = await send_invite(client, inviter, email, role)
    resp = await accept_invite(client, invite["invite_token"])
    assert resp.status_code == 200, resp.text
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    return in_tenant(headers, inviter["X-Tenant-Slug"])


@pytest.fixture
def create_tenant(
    client: AsyncClient, superadmin: AuthHeaders
) -> Callable[[str], Awaitable[AuthHeaders]]:
    """Superadmin creates a tenant and invites its tenantadmin; returns that admin's headers."""

    async def _create(slug: str) -> AuthHeaders:
        resp = await client.post(
            f"{API}/tenants", headers=superadmin, json={"name": slug.title(), "slug": slug}
        )
        assert resp.status_code == 201, resp.text
        return await invite_user(
            client, in_tenant(superadmin, slug), f"admin@{slug}.example.com", "tenantadmin"
        )

    return _create
