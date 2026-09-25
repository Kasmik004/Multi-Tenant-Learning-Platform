from httpx import AsyncClient

from tests.conftest import API, in_tenant, invite_user, send_invite


async def test_courses_are_invisible_across_tenants(client: AsyncClient, create_tenant) -> None:
    acme = await create_tenant("acme")
    globex = await create_tenant("globex")

    created = await client.post(f"{API}/courses", headers=acme, json={"title": "Acme 101"})
    assert created.status_code == 201
    course_id = created.json()["id"]

    # Owner sees it
    assert (await client.get(f"{API}/courses", headers=acme)).json()["total"] == 1

    # Other tenant sees nothing and cannot read, update, or delete it by id
    assert (await client.get(f"{API}/courses", headers=globex)).json()["total"] == 0
    assert (await client.get(f"{API}/courses/{course_id}", headers=globex)).status_code == 404
    patch = await client.patch(
        f"{API}/courses/{course_id}", headers=globex, json={"title": "hijacked"}
    )
    assert patch.status_code == 404
    delete = await client.delete(f"{API}/courses/{course_id}", headers=globex)
    assert delete.status_code == 404


async def test_users_are_invisible_across_tenants(client: AsyncClient, create_tenant) -> None:
    acme = await create_tenant("acme")
    globex = await create_tenant("globex")
    globex_user_id = (await send_invite(client, globex, "jane@example.com"))["user"]["id"]

    listed = await client.get(f"{API}/users", headers=acme)
    assert [u["email"] for u in listed.json()["items"]] == ["admin@acme.example.com"]

    # Guessing a globex user's id from acme finds nothing.
    patch = await client.patch(
        f"{API}/users/{globex_user_id}", headers=acme, json={"role": "tenantadmin"}
    )
    assert patch.status_code == 404
    assert (await client.delete(f"{API}/users/{globex_user_id}", headers=acme)).status_code == 404


async def test_header_cannot_reach_another_tenant(client: AsyncClient, create_tenant) -> None:
    acme = await create_tenant("acme")
    await create_tenant("globex")

    # acme's admin just swaps the header: the account belongs to acme, so no access.
    spoofed = in_tenant(acme, "globex")
    assert (await client.get(f"{API}/courses", headers=spoofed)).status_code == 403
    assert (await client.get(f"{API}/tenants/current", headers=spoofed)).status_code == 403
    invite = await client.post(
        f"{API}/users/invites", headers=spoofed, json={"email": "x@example.com"}
    )
    assert invite.status_code == 403

    # An unknown slug looks the same, so the header can't be used to probe slugs.
    unknown = await client.get(f"{API}/courses", headers=in_tenant(acme, "nope"))
    assert unknown.status_code == 403
    assert unknown.json() == (await client.get(f"{API}/courses", headers=spoofed)).json()


async def test_tenant_scoped_route_requires_header(client: AsyncClient, create_tenant) -> None:
    acme = await create_tenant("acme")
    no_header = {"Authorization": acme["Authorization"]}
    resp = await client.get(f"{API}/courses", headers=no_header)
    assert resp.status_code == 400
    assert "X-Tenant-Slug" in resp.json()["error"]["message"]


async def test_removed_user_loses_access_with_same_token(
    client: AsyncClient, create_tenant
) -> None:
    acme = await create_tenant("acme")
    jane = await invite_user(client, acme, "jane@example.com")
    jane_id = (await client.get(f"{API}/auth/me", headers=jane)).json()["id"]
    assert (await client.get(f"{API}/courses", headers=jane)).status_code == 200

    assert (await client.delete(f"{API}/users/{jane_id}", headers=acme)).status_code == 204
    assert (await client.get(f"{API}/courses", headers=jane)).status_code == 401
