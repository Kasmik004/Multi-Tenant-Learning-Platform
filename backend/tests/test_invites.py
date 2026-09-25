from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import update

from app.core.database import SessionLocal
from app.models import User
from tests.conftest import API, PASSWORD, accept_invite, login, send_invite


async def test_invited_user_joins_by_token_and_can_log_in(
    client: AsyncClient, create_tenant
) -> None:
    acme = await create_tenant("acme")
    invite = await send_invite(client, acme, "jane@example.com")
    assert invite["user"]["invite_pending"] is True

    # No password yet, so no login before accepting.
    resp = await client.post(
        f"{API}/auth/login",
        json={"email": "jane@example.com", "password": PASSWORD, "tenant_slug": "acme"},
    )
    assert resp.status_code == 401

    assert (await accept_invite(client, invite["invite_token"])).status_code == 200
    jane = await login(client, "jane@example.com", tenant="acme")
    me = (await client.get(f"{API}/auth/me", headers=jane)).json()
    assert (me["tenant_slug"], me["tenant_role"], me["invite_pending"]) == ("acme", "user", False)


async def test_invite_token_is_single_use(client: AsyncClient, create_tenant) -> None:
    acme = await create_tenant("acme")
    token = (await send_invite(client, acme, "jane@example.com"))["invite_token"]

    assert (await accept_invite(client, token)).status_code == 200
    # Replaying it can't reset the password.
    assert (await accept_invite(client, token, password="attacker-pass")).status_code == 401
    assert (await accept_invite(client, "made-up-token")).status_code == 401


async def test_expired_invite_is_rejected(client: AsyncClient, create_tenant) -> None:
    acme = await create_tenant("acme")
    token = (await send_invite(client, acme, "jane@example.com"))["invite_token"]
    async with SessionLocal() as session:
        await session.execute(
            update(User)
            .where(User.email == "jane@example.com")
            .values(invite_expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
        await session.commit()

    assert (await accept_invite(client, token)).status_code == 401


async def test_reinvite_replaces_pending_token(client: AsyncClient, create_tenant) -> None:
    acme = await create_tenant("acme")
    old = (await send_invite(client, acme, "jane@example.com"))["invite_token"]
    new = (await send_invite(client, acme, "jane@example.com"))["invite_token"]

    assert (await accept_invite(client, old)).status_code == 401
    assert (await accept_invite(client, new)).status_code == 200

    # Once accepted, the email is taken in this tenant.
    resp = await client.post(
        f"{API}/users/invites", headers=acme, json={"email": "JANE@example.com"}
    )
    assert resp.status_code == 409


async def test_accept_invite_validates_password(client: AsyncClient, create_tenant) -> None:
    acme = await create_tenant("acme")
    token = (await send_invite(client, acme, "jane@example.com"))["invite_token"]

    short = await accept_invite(client, token, password="short")
    assert short.status_code == 422
    mismatch = await client.post(
        f"{API}/auth/accept-invite",
        json={"token": token, "password": PASSWORD, "confirm_password": PASSWORD + "x"},
    )
    assert mismatch.status_code == 422
