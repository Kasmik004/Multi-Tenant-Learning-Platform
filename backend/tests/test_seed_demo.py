from httpx import AsyncClient

from app.cli import DEMO_PASSWORD, seed_demo
from tests.conftest import API, login


async def test_demo_accounts_can_log_in_and_learner_sees_course(client: AsyncClient) -> None:
    await seed_demo()
    await seed_demo()  # re-running doesn't duplicate anything

    superadmin = await login(client, "superadmin@demo.example.com", DEMO_PASSWORD)
    tenants = (await client.get(f"{API}/tenants", headers=superadmin)).json()
    assert [t["slug"] for t in tenants["items"]] == ["demo"]

    admin = await login(client, "admin@demo.example.com", DEMO_PASSWORD, tenant="demo")
    assert (await client.get(f"{API}/users", headers=admin)).json()["total"] == 2

    learner = await login(client, "learner@demo.example.com", DEMO_PASSWORD, tenant="demo")
    courses = (await client.get(f"{API}/courses", headers=learner)).json()
    assert [c["title"] for c in courses["items"]] == ["Getting started"]
    # Plain learner: no admin rights.
    assert (await client.get(f"{API}/users", headers=learner)).status_code == 403
