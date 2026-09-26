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

    # globex's user is untouched: still there, still a plain user.
    globex_users = (await client.get(f"{API}/users", headers=globex)).json()["items"]
    jane = next(u for u in globex_users if u["id"] == globex_user_id)
    assert jane["tenant_role"] == "user"


async def test_learner_cannot_open_another_tenants_course_by_id(
    client: AsyncClient, create_tenant
) -> None:
    acme = await create_tenant("acme")
    globex = await create_tenant("globex")
    jane = await invite_user(client, acme, "jane@example.com")
    globex_course = (
        await client.post(
            f"{API}/courses", headers=globex, json={"title": "Globex 101", "is_published": True}
        )
    ).json()["id"]

    assert (await client.get(f"{API}/courses/{globex_course}", headers=jane)).status_code == 404
    progress = f"{API}/courses/{globex_course}/progress"
    assert (await client.get(progress, headers=jane)).status_code == 404
    resp = await client.put(progress, headers=jane, json={"progress_percent": 100})
    assert resp.status_code == 404


async def test_tenant_admin_creates_only_in_own_tenant(client: AsyncClient, create_tenant) -> None:
    acme = await create_tenant("acme")
    globex = await create_tenant("globex")
    acme_id = (await client.get(f"{API}/tenants/current", headers=acme)).json()["id"]
    globex_id = (await client.get(f"{API}/tenants/current", headers=globex)).json()["id"]

    # A tenant_id in the body is ignored: the course lands in the caller's own tenant.
    resp = await client.post(
        f"{API}/courses", headers=acme, json={"title": "Sneaky", "tenant_id": globex_id}
    )
    assert resp.status_code == 201
    assert resp.json()["tenant_id"] == acme_id

    # Pointing the header at globex is refused for courses and for users.
    spoofed = in_tenant(acme, "globex")
    assert (
        await client.post(f"{API}/courses", headers=spoofed, json={"title": "X"})
    ).status_code == 403
    invite = await client.post(
        f"{API}/users/invites", headers=spoofed, json={"email": "x@example.com"}
    )
    assert invite.status_code == 403

    assert (await client.get(f"{API}/courses", headers=globex)).json()["total"] == 0
    assert (await client.get(f"{API}/users", headers=globex)).json()["total"] == 1


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


async def test_writes_without_tenant_context_are_rejected(
    client: AsyncClient, create_tenant
) -> None:
    acme = await create_tenant("acme")
    jane = await invite_user(client, acme, "jane@example.com")
    course_id = (await client.post(f"{API}/courses", headers=acme, json={"title": "A"})).json()[
        "id"
    ]
    jane_id = (await client.get(f"{API}/auth/me", headers=jane)).json()["id"]
    acme_id = (await client.get(f"{API}/tenants/current", headers=acme)).json()["id"]
    no_header = {"Authorization": acme["Authorization"]}

    # A tenant_id in the body doesn't stand in for the header.
    for path, body in (
        ("/courses", {"title": "B", "tenant_id": acme_id}),
        (f"/courses/{course_id}/enrollments", {"user_id": jane_id, "tenant_id": acme_id}),
        ("/users/invites", {"email": "x@example.com", "tenant_id": acme_id}),
    ):
        resp = await client.post(f"{API}{path}", headers=no_header, json=body)
        assert resp.status_code == 400, path

    assert (await client.get(f"{API}/courses", headers=acme)).json()["total"] == 1
    enrollments = await client.get(f"{API}/courses/{course_id}/enrollments", headers=acme)
    assert enrollments.json()["total"] == 0


async def test_removed_user_loses_access_with_same_token(
    client: AsyncClient, create_tenant
) -> None:
    acme = await create_tenant("acme")
    jane = await invite_user(client, acme, "jane@example.com")
    jane_id = (await client.get(f"{API}/auth/me", headers=jane)).json()["id"]
    assert (await client.get(f"{API}/courses", headers=jane)).status_code == 200

    assert (await client.delete(f"{API}/users/{jane_id}", headers=acme)).status_code == 204
    assert (await client.get(f"{API}/courses", headers=jane)).status_code == 401
