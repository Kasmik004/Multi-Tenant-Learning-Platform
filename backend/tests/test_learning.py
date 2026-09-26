from httpx import AsyncClient

from tests.conftest import API, assign_course, in_tenant, invite_user, user_id
from tests.test_platform_roles import platform_trio


async def test_users_see_only_assigned_published_courses(
    client: AsyncClient, create_tenant
) -> None:
    acme = await create_tenant("acme")
    jane = await invite_user(client, acme, "jane@example.com")
    bob = await invite_user(client, acme, "bob@example.com")
    assigned = await assign_course(client, acme, jane, "Assigned")
    draft = await assign_course(client, acme, jane, "Draft", published=False)
    other = (
        await client.post(
            f"{API}/courses", headers=acme, json={"title": "Other", "is_published": True}
        )
    ).json()["id"]

    listed = (await client.get(f"{API}/courses", headers=jane)).json()
    assert [c["title"] for c in listed["items"]] == ["Assigned"]
    assert (await client.get(f"{API}/courses/{assigned}", headers=jane)).status_code == 200
    for hidden in (draft, other):  # unpublished or not assigned: looks like it doesn't exist
        assert (await client.get(f"{API}/courses/{hidden}", headers=jane)).status_code == 404
    assert (await client.get(f"{API}/courses", headers=bob)).json()["total"] == 0
    # Tenantadmins still see every course.
    assert (await client.get(f"{API}/courses", headers=acme)).json()["total"] == 3

    mine = (await client.get(f"{API}/enrollments/me", headers=jane)).json()
    assert [e["course_id"] for e in mine["items"]] == [assigned]


async def test_assignment_rules(client: AsyncClient, create_tenant) -> None:
    acme = await create_tenant("acme")
    jane = await invite_user(client, acme, "jane@example.com")
    course_id = await assign_course(client, acme, jane)
    enroll = f"{API}/courses/{course_id}/enrollments"
    jane_id = await user_id(client, jane)

    again = await client.post(enroll, headers=acme, json={"user_id": jane_id})
    assert again.status_code == 409
    listed = (await client.get(enroll, headers=acme)).json()
    assert [(e["user_id"], e["status"]) for e in listed["items"]] == [(jane_id, "not_started")]

    # Plain users can't assign, see who's assigned, or unassign.
    assert (await client.post(enroll, headers=jane, json={"user_id": jane_id})).status_code == 403
    assert (await client.get(enroll, headers=jane)).status_code == 403
    assert (await client.delete(f"{enroll}/{jane_id}", headers=jane)).status_code == 403

    # Unassigning removes access (and the progress record).
    assert (await client.delete(f"{enroll}/{jane_id}", headers=acme)).status_code == 204
    assert (await client.get(f"{API}/courses/{course_id}", headers=jane)).status_code == 404
    assert (await client.delete(f"{enroll}/{jane_id}", headers=acme)).status_code == 404


async def test_progress_tracking(client: AsyncClient, create_tenant) -> None:
    acme = await create_tenant("acme")
    jane = await invite_user(client, acme, "jane@example.com")
    course_id = await assign_course(client, acme, jane)
    progress = f"{API}/courses/{course_id}/progress"

    first = (await client.get(progress, headers=jane)).json()
    assert (first["status"], first["progress_percent"]) == ("not_started", 0)

    half = (await client.put(progress, headers=jane, json={"progress_percent": 50})).json()
    assert (half["status"], half["completed_at"]) == ("in_progress", None)

    done = (await client.put(progress, headers=jane, json={"progress_percent": 100})).json()
    assert done["status"] == "completed"
    assert done["completed_at"] is not None
    # Saving 100 again keeps the original completion time.
    again = (await client.put(progress, headers=jane, json={"progress_percent": 100})).json()
    assert again["completed_at"] == done["completed_at"]

    # The admin sees it per course.
    listed = (await client.get(f"{API}/courses/{course_id}/enrollments", headers=acme)).json()
    assert listed["items"][0]["progress_percent"] == 100

    for bad in (-1, 101):
        resp = await client.put(progress, headers=jane, json={"progress_percent": bad})
        assert resp.status_code == 422


async def test_progress_needs_an_assignment(client: AsyncClient, create_tenant) -> None:
    acme = await create_tenant("acme")
    jane = await invite_user(client, acme, "jane@example.com")
    bob = await invite_user(client, acme, "bob@example.com")
    course_id = await assign_course(client, acme, jane)
    progress = f"{API}/courses/{course_id}/progress"

    assert (await client.get(progress, headers=bob)).status_code == 404
    resp = await client.put(progress, headers=bob, json={"progress_percent": 10})
    assert resp.status_code == 404

    # Unpublishing a course pauses it for learners without losing progress.
    await client.put(progress, headers=jane, json={"progress_percent": 30})
    await client.patch(f"{API}/courses/{course_id}", headers=acme, json={"is_published": False})
    assert (await client.get(progress, headers=jane)).status_code == 404
    await client.patch(f"{API}/courses/{course_id}", headers=acme, json={"is_published": True})
    assert (await client.get(progress, headers=jane)).json()["progress_percent"] == 30


async def test_enrollments_are_isolated_between_tenants(client: AsyncClient, create_tenant) -> None:
    acme = await create_tenant("acme")
    globex = await create_tenant("globex")
    jane = await invite_user(client, acme, "jane@example.com")
    course_id = await assign_course(client, acme, jane)
    enroll = f"{API}/courses/{course_id}/enrollments"
    jane_id = await user_id(client, jane)
    globex_admin_id = await user_id(client, globex)

    # globex's admin can't see, add to or remove acme's assignments by guessing ids.
    assert (await client.get(enroll, headers=globex)).status_code == 404
    resp = await client.post(enroll, headers=globex, json={"user_id": jane_id})
    assert resp.status_code == 404
    assert (await client.delete(f"{enroll}/{jane_id}", headers=globex)).status_code == 404
    # acme's admin can't assign a course to a user of another tenant.
    resp = await client.post(enroll, headers=acme, json={"user_id": globex_admin_id})
    assert resp.status_code == 404
    # Swapping the header doesn't help either.
    assert (await client.get(enroll, headers=in_tenant(jane, "globex"))).status_code == 403


async def test_platform_roles_cannot_touch_learning_data(
    client: AsyncClient, create_tenant
) -> None:
    acme = await create_tenant("acme")
    jane = await invite_user(client, acme, "jane@example.com")
    course_id = await assign_course(client, acme, jane)
    jane_id = await user_id(client, jane)

    for headers in await platform_trio(client, "acme"):
        for method, path, body in (
            ("GET", f"/courses/{course_id}/enrollments", None),
            ("POST", f"/courses/{course_id}/enrollments", {"user_id": jane_id}),
            ("DELETE", f"/courses/{course_id}/enrollments/{jane_id}", None),
            ("GET", f"/courses/{course_id}/progress", None),
            ("GET", "/enrollments/me", None),
        ):
            resp = await client.request(method, f"{API}{path}", headers=headers, json=body)
            assert resp.status_code == 403, (method, path)
