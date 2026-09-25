from httpx import AsyncClient

from tests.conftest import API, login


async def test_onboarding_creates_tenant_and_admin(client: AsyncClient, create_tenant) -> None:
    headers = await create_tenant("acme")

    me = await client.get(f"{API}/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["role"] == "admin"

    tenant = await client.get(f"{API}/tenants/current", headers=headers)
    assert tenant.json()["slug"] == "acme"


async def test_duplicate_slug_conflicts(client: AsyncClient, create_tenant) -> None:
    await create_tenant("acme")
    resp = await client.post(
        f"{API}/tenants",
        json={
            "name": "Other",
            "slug": "acme",
            "admin": {"email": "x@example.com", "full_name": "X", "password": "password123"},
        },
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "conflict"


async def test_login_rejects_wrong_password(client: AsyncClient, create_tenant) -> None:
    await create_tenant("acme")
    resp = await client.post(
        f"{API}/auth/login",
        json={
            "tenant_slug": "acme",
            "email": "admin@acme.example.com",
            "password": "wrong-password",
        },
    )
    assert resp.status_code == 401


async def test_missing_token_is_unauthorized(client: AsyncClient) -> None:
    resp = await client.get(f"{API}/auth/me")
    assert resp.status_code == 401


async def test_learner_cannot_create_course_or_users(client: AsyncClient, create_tenant) -> None:
    admin = await create_tenant("acme")
    resp = await client.post(
        f"{API}/users",
        headers=admin,
        json={"email": "learner@acme.example.com", "full_name": "L", "password": "password123"},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "learner"

    learner = await login(client, "acme", "learner@acme.example.com", "password123")
    assert (
        await client.post(f"{API}/courses", headers=learner, json={"title": "X"})
    ).status_code == 403
    assert (await client.get(f"{API}/users", headers=learner)).status_code == 403


async def test_register_creates_user_with_default_role(client: AsyncClient, create_tenant) -> None:
    await create_tenant("acme")
    resp = await client.post(
        f"{API}/auth/register",
        json={
            "tenant_slug": "acme",
            "email": "reg@acme.example.com",
            "password": "password123",
            "confirm_password": "password123",
        },
    )
    assert resp.status_code == 200, resp.text

    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    me = await client.get(f"{API}/auth/me", headers=headers)
    assert me.status_code == 200, me.text
    assert me.json()["role"] == "user"
    assert me.json()["full_name"] is None

    tenant = await client.get(f"{API}/tenants/current", headers=headers)
    assert tenant.json()["slug"] == "acme"


async def test_registered_user_can_log_in(client: AsyncClient, create_tenant) -> None:
    await create_tenant("acme")
    resp = await client.post(
        f"{API}/auth/register",
        json={
            "tenant_slug": "acme",
            "email": "reg@acme.example.com",
            "password": "password123",
            "confirm_password": "password123",
        },
    )
    assert resp.status_code == 200, resp.text

    headers = await login(client, "acme", "reg@acme.example.com", "password123")
    me = await client.get(f"{API}/auth/me", headers=headers)
    assert me.json()["email"] == "reg@acme.example.com"
