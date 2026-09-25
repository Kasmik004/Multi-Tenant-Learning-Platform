from httpx import AsyncClient

from app.models import PlatformRole
from tests.conftest import API, create_platform_user, in_tenant, invite_user


async def test_only_superadmin_creates_and_deletes_tenants(
    client: AsyncClient, create_tenant
) -> None:
    await create_tenant("acme")
    admin = await create_platform_user(client, "admin@platform.example.com", PlatformRole.ADMIN)
    viewer = await create_platform_user(
        client, "viewer@platform.example.com", PlatformRole.SUPERVIEWER
    )
    tenantadmin = await client.post(
        f"{API}/tenants",
        headers={"Authorization": (await create_tenant("globex"))["Authorization"]},
        json={"name": "X", "slug": "x"},
    )
    assert tenantadmin.status_code == 403

    for caller in (admin, viewer):
        body = {"name": "New", "slug": "new"}
        assert (await client.post(f"{API}/tenants", headers=caller, json=body)).status_code == 403
        assert (await client.delete(f"{API}/tenants/acme", headers=caller)).status_code == 403


async def test_admin_can_update_tenant_but_superviewer_cannot(
    client: AsyncClient, create_tenant
) -> None:
    await create_tenant("acme")
    admin = await create_platform_user(client, "admin@platform.example.com", PlatformRole.ADMIN)
    viewer = await create_platform_user(
        client, "viewer@platform.example.com", PlatformRole.SUPERVIEWER
    )

    body = {"name": "Acme Corp"}
    assert (await client.patch(f"{API}/tenants/acme", headers=viewer, json=body)).status_code == 403
    resp = await client.patch(f"{API}/tenants/acme", headers=admin, json=body)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Acme Corp"

    listed = await client.get(f"{API}/tenants", headers=viewer)
    assert [t["slug"] for t in listed.json()["items"]] == ["acme"]


async def test_tenant_user_cannot_list_tenants(client: AsyncClient, create_tenant) -> None:
    jane = await invite_user(client, await create_tenant("acme"), "jane@example.com")
    assert (await client.get(f"{API}/tenants", headers=jane)).status_code == 403


async def test_tenant_user_cannot_manage_tenant(client: AsyncClient, create_tenant) -> None:
    acme = await create_tenant("acme")
    jane = await invite_user(client, acme, "jane@example.com")
    jane_id = (await client.get(f"{API}/auth/me", headers=jane)).json()["id"]

    assert (await client.get(f"{API}/courses", headers=jane)).status_code == 200
    assert (
        await client.post(f"{API}/courses", headers=jane, json={"title": "X"})
    ).status_code == 403
    assert (await client.get(f"{API}/users", headers=jane)).status_code == 403
    invite = await client.post(f"{API}/users/invites", headers=jane, json={"email": "x@y.com"})
    assert invite.status_code == 403
    promote = await client.patch(
        f"{API}/users/{jane_id}", headers=jane, json={"role": "tenantadmin"}
    )
    assert promote.status_code == 403


async def test_superviewer_reads_any_tenant_but_cannot_write(
    client: AsyncClient, create_tenant
) -> None:
    acme = await create_tenant("acme")
    await client.post(f"{API}/courses", headers=acme, json={"title": "Acme 101"})
    viewer = in_tenant(
        await create_platform_user(client, "viewer@platform.example.com", PlatformRole.SUPERVIEWER),
        "acme",
    )

    assert (await client.get(f"{API}/courses", headers=viewer)).json()["total"] == 1
    assert (await client.get(f"{API}/users", headers=viewer)).status_code == 200
    resp = await client.post(f"{API}/courses", headers=viewer, json={"title": "X"})
    assert resp.status_code == 403
    invite = await client.post(f"{API}/users/invites", headers=viewer, json={"email": "x@y.com"})
    assert invite.status_code == 403


async def test_platform_admin_manages_any_tenant(client: AsyncClient, create_tenant) -> None:
    await create_tenant("acme")
    admin = in_tenant(
        await create_platform_user(client, "admin@platform.example.com", PlatformRole.ADMIN),
        "acme",
    )
    assert (
        await client.post(f"{API}/courses", headers=admin, json={"title": "X"})
    ).status_code == 201


async def test_members_lose_access_to_deactivated_tenant(
    client: AsyncClient, create_tenant, superadmin
) -> None:
    acme = await create_tenant("acme")
    resp = await client.patch(f"{API}/tenants/acme", headers=superadmin, json={"is_active": False})
    assert resp.status_code == 200

    assert (await client.get(f"{API}/courses", headers=acme)).status_code == 403
    # Platform roles still reach it so they can manage it.
    assert (
        await client.get(f"{API}/courses", headers=in_tenant(superadmin, "acme"))
    ).status_code == 200
