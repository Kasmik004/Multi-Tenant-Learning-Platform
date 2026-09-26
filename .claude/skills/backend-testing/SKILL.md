---
name: backend-testing
description: How to run and write backend tests (pytest integration tests against real Postgres) - reusable fixtures for tenants, invites, logins and platform roles, the tenant-isolation test pattern, and what AGENT.md requires tests to cover. Load before adding or changing backend tests, before reporting any backend task done, or when a backend test fails.
---

# Backend testing

Integration tests hit a real Postgres DB through the ASGI app (no mocks). Run from `backend/`:

```bash
uv run pytest -q                      # full suite; required before reporting done
uv run pytest -q tests/test_invites.py -k expired
```

Needs Postgres on `localhost:5432` (`docker compose up -d db`). Tests use their own DB,
`learning_platform_test` (override with `POSTGRES_TEST_DB`), created automatically. Each session
**drops and recreates the `public` schema**, then runs `Base.metadata.create_all` (models, not
migrations), and every table is truncated after each test. Never point tests at the dev DB.

Also run before done: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy app`
(same as CI in `.github/workflows/ci.yml`).

## AGENT.md requirements

- New feature: at least one main-behavior test plus one edge case.
- Bug fix: a regression test that fails on the old code (check it does) and passes on the fix.
- Never skip or comment out a failing test; fix it or report it.
- Focus areas: authentication/authorization, role permissions, **tenant isolation**, tenant
  expiration (trial expiry, deactivation), course assignment, learning progress. Meaningful cases, not coverage.
- Reuse the fixtures below instead of re-writing setup flows.

## Fixtures and helpers (`tests/conftest.py`)

| Name | Gives you |
|---|---|
| `client` (fixture) | `httpx.AsyncClient` bound to the app |
| `API` | `"/api/v1"` prefix |
| `superadmin` (fixture) | headers of a platform superadmin (no tenant) |
| `create_tenant` (fixture) | `await create_tenant("acme")` → superadmin creates tenant, invites + accepts `admin@acme.example.com` as tenantadmin; returns **that admin's headers incl. `X-Tenant-Slug`** |
| `invite_user(client, inviter, email, role="user")` | full invite → accept flow; returns the new user's headers scoped to the inviter's tenant |
| `send_invite(client, inviter, email, role)` | just the invite; returns body with `invite_token`, `user` |
| `accept_invite(client, token, password=PASSWORD)` | raw `Response` of accept-invite |
| `login(client, email, password=PASSWORD, tenant=None)` | login; with `tenant`, headers include the slug |
| `in_tenant(headers, slug)` | same caller with a different `X-Tenant-Slug` (spoofing tests) |
| `create_platform_user(client, email, PlatformRole.X)` | seeds a platform account in the DB, returns headers |
| `user_id(client, headers)` | the caller's user id (from `/auth/me`) |
| `assign_course(client, admin, learner, title=, published=True)` | creates a course and assigns it to `learner`; returns its id |
| `set_trial_end(slug, when)` | moves a tenant's `trial_ends_at` (e.g. into the past to test expiry) |
| `PASSWORD`, `AuthHeaders` | default password, headers type |

`tests/test_platform_roles.py::platform_trio(client, slug)` returns superadmin, admin and
superviewer headers pointed at a tenant, for "every platform role gets 403" loops.

## Test files

- `test_auth_and_tenants.py`: login (wrong password, wrong/missing tenant), token contents, per-tenant accounts.
- `test_invites.py`: invite → accept, single-use and expired tokens, re-invite, password validation.
- `test_tenant_isolation.py`: cross-tenant access by id and by header, header required, removal is immediate.
- `test_platform_roles.py`: tenant CRUD rights, platform roles see metadata only, invite restrictions.
- `test_learning.py`: assignment rules, learners see only assigned+published courses, progress,
  enrollment isolation, platform roles blocked.
- `test_trial_lifecycle.py`: trial start, expiry blocks courses/invites (not sign-in), sweep is
  idempotent, extend/reactivate keeps data, who may extend.

## Pattern: every new tenant-owned resource gets an isolation test

```python
async def test_widgets_are_invisible_across_tenants(client, create_tenant) -> None:
    acme = await create_tenant("acme")
    globex = await create_tenant("globex")
    wid = (await client.post(f"{API}/widgets", headers=acme, json={...})).json()["id"]

    assert (await client.get(f"{API}/widgets", headers=globex)).json()["total"] == 0
    for method in ("GET", "PATCH", "DELETE"):  # guessing the id from another tenant -> 404
        resp = await client.request(method, f"{API}/widgets/{wid}", headers=globex,
                                    json={} if method == "PATCH" else None)
        assert resp.status_code == 404
    # and the header can't be swapped to reach it
    assert (await client.get(f"{API}/widgets", headers=in_tenant(globex, "acme"))).status_code == 403
```

Also add a role test: a plain `user` (via `invite_user`) gets 403 on manager-only actions, and
platform roles get 403 on tenant data (see `platform_trio`).

To manipulate state HTTP can't reach (e.g. expire an invite), use `SessionLocal()` from
`app.core.database` directly in the test, as `test_expired_invite_is_rejected` does.
