from httpx import AsyncClient

from tests.conftest import API


async def test_liveness(client: AsyncClient) -> None:
    resp = await client.get(f"{API}/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_readiness_checks_database(client: AsyncClient) -> None:
    resp = await client.get(f"{API}/health/ready")
    assert resp.status_code == 200
    assert resp.json()["database"] == "ok"
