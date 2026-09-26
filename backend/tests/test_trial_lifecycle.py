from datetime import UTC, datetime, timedelta

from httpx import AsyncClient

from app.core.config import settings
from app.core.database import SessionLocal
from app.services import TenantService
from tests.conftest import (
    API,
    AuthHeaders,
    assign_course,
    in_tenant,
    invite_user,
    login,
    set_trial_end,
)
from tests.test_platform_roles import platform_trio

PAST = datetime.now(UTC) - timedelta(minutes=1)


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value)


async def _expire_trials() -> list[str]:
    async with SessionLocal() as session:
        return list(await TenantService(session).expire_trials())


async def test_new_tenant_starts_a_trial(client: AsyncClient, create_tenant) -> None:
    acme = await create_tenant("acme")

    tenant = (await client.get(f"{API}/tenants/current", headers=acme)).json()
    assert tenant["status"] == "trial_active"
    assert tenant["expired_at"] is None
    trial_length = _parse(tenant["trial_ends_at"]) - _parse(tenant["created_at"])
    assert abs(trial_length - timedelta(days=settings.TRIAL_DAYS)) < timedelta(minutes=1)


async def test_expired_trial_blocks_learning_but_keeps_accounts(
    client: AsyncClient, create_tenant, superadmin: AuthHeaders
) -> None:
    acme = await create_tenant("acme")
    learner = await invite_user(client, acme, "jane@example.com")
    course = await client.post(f"{API}/courses", headers=acme, json={"title": "Acme 101"})
    course_id = course.json()["id"]

    # No sweep has run: passing trial_ends_at alone is enough to block access.
    await set_trial_end("acme", PAST)

    blocked = [
        await client.get(f"{API}/courses", headers=learner),
        await client.get(f"{API}/courses/{course_id}", headers=learner),
        await client.post(f"{API}/courses", headers=acme, json={"title": "New"}),
        await client.patch(f"{API}/courses/{course_id}", headers=acme, json={"title": "x"}),
        await client.delete(f"{API}/courses/{course_id}", headers=acme),
        await client.post(f"{API}/users/invites", headers=acme, json={"email": "b@example.com"}),
        await client.post(
            f"{API}/users/invites",
            headers=in_tenant(superadmin, "acme"),
            json={"email": "boss@example.com", "role": "tenantadmin"},
        ),
    ]
    for resp in blocked:
        assert resp.status_code == 403, resp.text
        assert resp.json()["error"]["code"] == "trial_expired"

    # Accounts still work: sign in, see why access is limited, manage existing users.
    await login(client, "jane@example.com", tenant="acme")
    current = await client.get(f"{API}/tenants/current", headers=learner)
    assert current.json()["status"] == "expired"
    assert (await client.get(f"{API}/auth/me", headers=learner)).status_code == 200
    assert (await client.get(f"{API}/users", headers=acme)).json()["total"] == 2


async def test_expired_trial_blocks_assignments_and_progress(
    client: AsyncClient, create_tenant
) -> None:
    acme = await create_tenant("acme")
    learner = await invite_user(client, acme, "jane@example.com")
    course_id = await assign_course(client, acme, learner)
    learner_id = (await client.get(f"{API}/auth/me", headers=learner)).json()["id"]
    await set_trial_end("acme", PAST)
    await _expire_trials()  # recorded as expired, like after the scheduled job

    enroll = f"{API}/courses/{course_id}/enrollments"
    progress = f"{API}/courses/{course_id}/progress"
    for method, url, headers, body in (
        ("GET", f"{API}/enrollments/me", learner, None),
        ("GET", progress, learner, None),
        ("PUT", progress, learner, {"progress_percent": 50}),
        ("GET", enroll, acme, None),
        ("POST", enroll, acme, {"user_id": learner_id}),
        ("DELETE", f"{enroll}/{learner_id}", acme, None),
    ):
        resp = await client.request(method, url, headers=headers, json=body)
        assert resp.status_code == 403, (method, url)
        assert resp.json()["error"]["code"] == "trial_expired"


async def test_expired_trial_does_not_affect_other_tenants(
    client: AsyncClient, create_tenant
) -> None:
    await create_tenant("acme")
    globex = await create_tenant("globex")
    await set_trial_end("acme", PAST)

    assert (await client.get(f"{API}/courses", headers=globex)).status_code == 200
    assert await _expire_trials() == ["acme"]


async def test_sweep_records_each_expiry_once(
    client: AsyncClient, create_tenant, superadmin: AuthHeaders
) -> None:
    await create_tenant("acme")
    await create_tenant("globex")
    await set_trial_end("acme", PAST)

    assert await _expire_trials() == ["acme"]
    first = (await client.get(f"{API}/tenants/acme", headers=superadmin)).json()
    assert first["status"] == "expired"
    assert first["expired_at"] is not None

    # Running it again is a no-op: nothing re-expired, the original timestamp is kept.
    assert await _expire_trials() == []
    again = (await client.get(f"{API}/tenants/acme", headers=superadmin)).json()
    assert again["expired_at"] == first["expired_at"]
    globex = (await client.get(f"{API}/tenants/globex", headers=superadmin)).json()
    assert globex["status"] == "trial_active"


async def test_extending_trial_reactivates_tenant_with_its_data(
    client: AsyncClient, create_tenant, superadmin: AuthHeaders
) -> None:
    acme = await create_tenant("acme")
    learner = await invite_user(client, acme, "jane@example.com")
    course_id = await assign_course(client, acme, learner)
    progress = f"{API}/courses/{course_id}/progress"
    await client.put(progress, headers=learner, json={"progress_percent": 40})
    await set_trial_end("acme", PAST)
    assert (await client.put(progress, headers=learner, json={"progress_percent": 90})).json()[
        "error"
    ]["code"] == "trial_expired"
    await _expire_trials()

    resp = await client.post(f"{API}/tenants/acme/trial", headers=superadmin, json={"days": 7})
    assert resp.status_code == 200, resp.text
    tenant = resp.json()
    assert tenant["status"] == "trial_active"
    assert tenant["expired_at"] is None
    # An expired trial restarts from now, not from the old end date.
    remaining = _parse(tenant["trial_ends_at"]) - datetime.now(UTC)
    assert timedelta(days=7) - timedelta(minutes=1) < remaining <= timedelta(days=7)

    courses = await client.get(f"{API}/courses", headers=learner)
    assert courses.status_code == 200
    assert [c["title"] for c in courses.json()["items"]] == ["Acme 101"]
    # Progress made before the expiry is kept.
    assert (await client.get(progress, headers=learner)).json()["progress_percent"] == 40
    # The sweep doesn't undo the reactivation.
    assert await _expire_trials() == []


async def test_extending_running_trial_adds_to_it(
    client: AsyncClient, create_tenant, superadmin: AuthHeaders
) -> None:
    await create_tenant("acme")
    before = (await client.get(f"{API}/tenants/acme", headers=superadmin)).json()

    resp = await client.post(f"{API}/tenants/acme/trial", headers=superadmin, json={"days": 3})
    added = _parse(resp.json()["trial_ends_at"]) - _parse(before["trial_ends_at"])
    assert added == timedelta(days=3)


async def test_only_platform_admins_can_extend_trials(client: AsyncClient, create_tenant) -> None:
    acme = await create_tenant("acme")
    superadmin, admin, superviewer = await platform_trio(client, "acme")
    learner = await invite_user(client, acme, "jane@example.com")

    for headers in (acme, learner, superviewer):
        resp = await client.post(f"{API}/tenants/acme/trial", headers=headers, json={"days": 7})
        assert resp.status_code == 403
    for headers in (superadmin, admin):
        resp = await client.post(f"{API}/tenants/acme/trial", headers=headers, json={"days": 7})
        assert resp.status_code == 200

    for days in (0, 366):
        resp = await client.post(
            f"{API}/tenants/acme/trial", headers=superadmin, json={"days": days}
        )
        assert resp.status_code == 422
    missing = await client.post(f"{API}/tenants/nope/trial", headers=superadmin, json={"days": 7})
    assert missing.status_code == 404
