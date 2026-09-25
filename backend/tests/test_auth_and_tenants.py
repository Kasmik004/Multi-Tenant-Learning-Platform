import jwt
from httpx import AsyncClient

from app.core.config import settings
from tests.conftest import API, PASSWORD, in_tenant, invite_user, login


async def test_tenant_admin_is_set_up_by_invite(client: AsyncClient, create_tenant) -> None:
    headers = await create_tenant("acme")

    me = (await client.get(f"{API}/auth/me", headers=headers)).json()
    assert me["tenant_slug"] == "acme"
    assert me["tenant_role"] == "tenantadmin"
    assert me["platform_role"] is None

    tenant = await client.get(f"{API}/tenants/current", headers=headers)
    assert tenant.json()["slug"] == "acme"


async def test_duplicate_slug_conflicts(client: AsyncClient, superadmin) -> None:
    body = {"name": "Acme", "slug": "acme"}
    assert (await client.post(f"{API}/tenants", headers=superadmin, json=body)).status_code == 201
    resp = await client.post(f"{API}/tenants", headers=superadmin, json=body)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "conflict"


async def test_login_rejects_wrong_password(client: AsyncClient, create_tenant) -> None:
    await create_tenant("acme")
    resp = await client.post(
        f"{API}/auth/login",
        json={"email": "admin@acme.example.com", "password": "wrong", "tenant_slug": "acme"},
    )
    assert resp.status_code == 401


async def test_login_only_into_own_tenant(client: AsyncClient, create_tenant) -> None:
    await create_tenant("acme")
    await create_tenant("globex")
    for slug in ("globex", None, "nope"):
        resp = await client.post(
            f"{API}/auth/login",
            json={"email": "admin@acme.example.com", "password": PASSWORD, "tenant_slug": slug},
        )
        assert resp.status_code == 401, slug


async def test_missing_token_is_unauthorized(client: AsyncClient) -> None:
    resp = await client.get(f"{API}/auth/me")
    assert resp.status_code == 401


async def test_token_carries_identity_only(client: AsyncClient, create_tenant) -> None:
    await create_tenant("acme")
    resp = await client.post(
        f"{API}/auth/login",
        json={"email": "admin@acme.example.com", "password": PASSWORD, "tenant_slug": "acme"},
    )
    payload = jwt.decode(
        resp.json()["access_token"], settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
    assert set(payload) == {"sub", "iat", "exp"}


async def test_same_email_is_a_separate_account_per_tenant(
    client: AsyncClient, create_tenant
) -> None:
    acme = await create_tenant("acme")
    globex = await create_tenant("globex")
    await invite_user(client, acme, "jane@example.com")
    await invite_user(client, globex, "jane@example.com", role="tenantadmin")

    jane_acme = await login(client, "jane@example.com", tenant="acme")
    jane_globex = await login(client, "jane@example.com", tenant="globex")
    acme_me = (await client.get(f"{API}/auth/me", headers=jane_acme)).json()
    globex_me = (await client.get(f"{API}/auth/me", headers=jane_globex)).json()
    assert acme_me["id"] != globex_me["id"]
    assert (acme_me["tenant_role"], globex_me["tenant_role"]) == ("user", "tenantadmin")

    # The acme account can't reach globex, even though the email matches.
    resp = await client.get(f"{API}/courses", headers=in_tenant(jane_acme, "globex"))
    assert resp.status_code == 403
