from httpx import AsyncClient

from tests.conftest import API


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


async def test_same_email_allowed_in_different_tenants(client: AsyncClient, create_tenant) -> None:
    acme = await create_tenant("acme")
    globex = await create_tenant("globex")
    body = {"email": "jane@example.com", "full_name": "Jane", "password": "password123"}

    assert (await client.post(f"{API}/users", headers=acme, json=body)).status_code == 201
    assert (await client.post(f"{API}/users", headers=globex, json=body)).status_code == 201
    assert (await client.post(f"{API}/users", headers=acme, json=body)).status_code == 409
