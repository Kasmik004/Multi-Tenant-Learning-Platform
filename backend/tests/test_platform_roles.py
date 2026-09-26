from httpx import AsyncClient

from app.models import PlatformRole
from tests.conftest import (
    API,
    AuthHeaders,
    create_platform_user,
    in_tenant,
    invite_user,
    send_invite,
)


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


async def test_tenant_accounts_cannot_create_tenants(
    client: AsyncClient, create_tenant, superadmin
) -> None:
    acme = await create_tenant("acme")
    jane = await invite_user(client, acme, "jane@example.com")

    for caller in (acme, jane):
        resp = await client.post(f"{API}/tenants", headers=caller, json={"name": "X", "slug": "x"})
        assert resp.status_code == 403
    listed = await client.get(f"{API}/tenants", headers=superadmin)
    assert [t["slug"] for t in listed.json()["items"]] == ["acme"]


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


async def platform_trio(client: AsyncClient, slug: str) -> list[AuthHeaders]:
    """superadmin, admin and superviewer headers, all pointed at `slug`."""
    return [
        in_tenant(await create_platform_user(client, f"{role}@platform.example.com", role), slug)
        for role in PlatformRole
    ]


async def test_platform_roles_see_tenant_metadata_but_no_tenant_data(
    client: AsyncClient, create_tenant
) -> None:
    acme = await create_tenant("acme")
    course_id = (
        await client.post(f"{API}/courses", headers=acme, json={"title": "Acme 101"})
    ).json()["id"]
    admin_id = (await client.get(f"{API}/auth/me", headers=acme)).json()["id"]

    for caller in await platform_trio(client, "acme"):
        assert (await client.get(f"{API}/tenants/current", headers=caller)).status_code == 200
        # Users' PII and the tenant's courses stay inside the tenant.
        for method, path in [
            ("GET", "/users"),
            ("PATCH", f"/users/{admin_id}"),
            ("DELETE", f"/users/{admin_id}"),
            ("GET", "/courses"),
            ("GET", f"/courses/{course_id}"),
            ("POST", "/courses"),
        ]:
            body = {"role": "user"} if method == "PATCH" else {"title": "X"}
            resp = await client.request(
                method, f"{API}{path}", headers=caller, json=body if method != "GET" else None
            )
            assert resp.status_code == 403, (caller, method, path)


async def test_platform_admins_invite_only_tenant_admins(
    client: AsyncClient, create_tenant
) -> None:
    await create_tenant("acme")
    superadmin, admin, viewer = await platform_trio(client, "acme")

    for i, caller in enumerate((superadmin, admin)):
        email = f"boss{i}@acme.example.com"
        ok = await client.post(
            f"{API}/users/invites", headers=caller, json={"email": email, "role": "tenantadmin"}
        )
        assert ok.status_code == 201, ok.text
        learner = await client.post(
            f"{API}/users/invites", headers=caller, json={"email": "l@x.com", "role": "user"}
        )
        assert learner.status_code == 403

    denied = await client.post(
        f"{API}/users/invites", headers=viewer, json={"email": "v@x.com", "role": "tenantadmin"}
    )
    assert denied.status_code == 403


async def test_tenant_admin_invites_users_and_admins(client: AsyncClient, create_tenant) -> None:
    acme = await create_tenant("acme")
    for role in ("user", "tenantadmin"):
        await send_invite(client, acme, f"{role}@acme.example.com", role)


async def test_members_lose_access_to_deactivated_tenant(
    client: AsyncClient, create_tenant, superadmin
) -> None:
    acme = await create_tenant("acme")
    resp = await client.patch(f"{API}/tenants/acme", headers=superadmin, json={"is_active": False})
    assert resp.status_code == 200

    assert (await client.get(f"{API}/courses", headers=acme)).status_code == 403
    # Platform roles still see its metadata so they can reactivate it.
    current = await client.get(f"{API}/tenants/current", headers=in_tenant(superadmin, "acme"))
    assert current.json()["is_active"] is False
