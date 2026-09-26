---
name: backend-architecture
description: How the FastAPI backend (backend/) is built - multi-tenancy model, auth (JWT + X-Tenant-Slug header + invites), the five roles and their exact permissions, layering rules, and the checklist for adding a feature or endpoint. Load before changing anything under backend/app, adding an endpoint/model/service, touching auth or permissions, or answering questions about roles, tenants or the API.
---

# Backend architecture

Multi-tenant learning platform. Each **tenant** is a separate institute/organization; its data
must never be reachable from another tenant, even by guessing IDs. Read `AGENT.md` at the repo
root too: it has binding rules (ask before auth/permission/architecture decisions, migrations,
tests, `CHANGES.md` entries).

Stack: FastAPI, SQLAlchemy 2 async + asyncpg, Alembic, Pydantic v2, PostgreSQL 17, `uv`.
Run everything from `backend/` with `uv run ...`.

## Layers (backend/app)

| Layer | Rule |
|---|---|
| `api/v1/endpoints/*` | Thin: pick the permission dependency, call a service, map to a schema. No queries. |
| `api/deps.py` | Auth + permission dependencies (see below). All access control lives here. |
| `services/*` | Business logic. **Services own the transaction** (`await self.session.commit()`). Raise `app.core.exceptions` errors, never `HTTPException`. |
| `repositories/*` | Data access. Flush, never commit. Tenant data goes through `TenantScopedRepository`, which adds `WHERE tenant_id = ?` to every query. |
| `models/*` | SQLAlchemy models. Tenant-owned tables use `TenantScopedMixin`. Import new models in `models/__init__.py`. |
| `schemas/*` | Pydantic request/response models; `ORMModel` for responses built from ORM objects. |
| `core/` | settings (`config.py`), DB session, `security.py` (JWT, password + invite-token hashing), errors. |

Errors: `NotFoundError` 404, `ConflictError` 409, `UnauthorizedError` 401, `ForbiddenError` 403,
`AppError` 400. The response shape is `{"error": {"code", "message"}}`.

## Tenancy and auth

- **Accounts are per tenant.** `users.tenant_id` + `users.tenant_role` (`tenantadmin` | `user`).
  The same email may have separate accounts in different tenants (unique on `(tenant_id, email)`).
- **Platform accounts** have `tenant_id IS NULL` and a `platform_role` (unique email among them).
- **JWT carries identity only** (`sub`, `iat`, `exp`). Roles and tenant are read from the DB on
  every request, so removing a user or changing a role takes effect immediately.
- **Tenant per request comes from the `X-Tenant-Slug` header.** `get_tenant_context` returns 400
  without it and the *same* 403 for an unknown slug or another tenant (no slug probing).
- **Login:** `POST /auth/login {email, password, tenant_slug}`; omit `tenant_slug` for platform
  accounts (a tenant account can't log in without its slug).
- **Onboarding is invite-only.** No self-registration, no public tenant list.
  1. `POST /users/invites {email, full_name?, role}` → returns a one-time `invite_token`
     (only its sha256 is stored; 72h, `INVITE_EXPIRE_HOURS`). Email delivery isn't built yet.
     Re-inviting a still-pending email replaces the old token.
  2. `POST /auth/accept-invite {token, password, confirm_password}` → sets the password, burns the
     token, returns an access token. Pending accounts (`hashed_password IS NULL`) can't log in.
- First superadmin: `uv run python -m app.cli create-superadmin <email>` (never over HTTP).

## Roles and permissions (source of truth: `api/deps.py`)

| Capability | superadmin | admin | superviewer | tenantadmin | user |
|---|---|---|---|---|---|
| Create / delete tenants | ✅ | | | | |
| Update tenants (`PATCH /tenants/{slug}`) | ✅ | ✅ | | | |
| List / get any tenant's metadata | ✅ | ✅ | ✅ | | |
| `GET /tenants/current` | ✅ any | ✅ any | ✅ any | own | own |
| Invite a **tenantadmin** | ✅ | ✅ | | ✅ | |
| Invite a **user** | | | | ✅ | |
| List / change role / remove users | | | | ✅ | |
| Read courses | | | | ✅ all | ✅ assigned + published |
| Create / edit / delete courses | | | | ✅ | |
| Assign / unassign courses, see progress per course | | | | ✅ | |
| Read / update own progress, `GET /enrollments/me` | | | | ✅ | ✅ |
| Extend a trial (`POST /tenants/{slug}/trial`) | ✅ | ✅ | | | |

Platform roles see **tenant metadata only**: never a tenant's users (PII) or courses.
Members of a deactivated tenant are locked out; platform roles can still see and reactivate it.

**Free trial** (`docs/tenant-trial.md`): tenants start `trial_active` with
`trial_ends_at = created + TRIAL_DAYS`. Once it passes (checked per request via
`tenant.trial_expired`, not waiting for the `expire-trials` sweep), courses and invites return
403 `trial_expired`; sign-in, `/tenants/current` and user management still work. Superadmin/admin
extend or reactivate with `POST /tenants/{slug}/trial {days}`.

Permission dependencies to use in endpoints:

- `CurrentUser`: any authenticated account (no tenant).
- `SuperAdminUser`, `PlatformAdminUser` (superadmin+admin), `PlatformUser` (any platform role).
- `TenantScope`: tenant metadata; the tenant's own accounts plus platform roles.
- `TenantMember`: the tenant's own accounts only. **Default for tenant data.**
- `TenantManager`: the tenant's own tenantadmins.
- `TenantInviter`: TenantManager + superadmin/admin (endpoint forbids them any role but tenantadmin).
  Requires a running trial.
- `LearningMember` / `LearningManager`: `TenantMember` / `TenantManager` + a running trial.
  **Use these for every learning feature** (courses, enrollment, progress).

Each gives a `TenantContext` (`ctx.user`, `ctx.tenant`, `ctx.tenant_id`, `ctx.is_platform`).

## API map (`/api/v1`)

`GET /health`, `GET /health/ready` · `POST /auth/login`, `POST /auth/accept-invite`,
`GET /auth/me` (includes `tenant_slug` to send as the header) · `POST|GET /tenants`,
`GET /tenants/current`, `GET|PATCH|DELETE /tenants/{slug}`, `POST /tenants/{slug}/trial` · `GET /users`,
`POST /users/invites`, `PATCH|DELETE /users/{user_id}` · `GET|POST /courses`,
`GET|PATCH|DELETE /courses/{course_id}`, `POST|GET /courses/{id}/enrollments`,
`DELETE /courses/{id}/enrollments/{user_id}`, `GET|PUT /courses/{id}/progress`,
`GET /enrollments/me`.

**Learning:** `Enrollment` (tenant-scoped, unique per course+user) = assignment + progress.
`CourseRepository(..., learner_id=)` limits a plain user to published courses assigned to them
(others 404). Progress status is derived from `progress_percent` (0 / 1-99 / 100);
`completed_at` is set the first time it reaches 100. Unassigning, deleting the course or
removing the user deletes the enrollment (FK cascade).

## Adding a tenant-owned feature (checklist)

1. Model with `TenantScopedMixin`; export it from `models/__init__.py`.
2. Repository subclassing `TenantScopedRepository[Model]`. Never query tenant data with plain
   `select()` outside it; that is how cross-tenant leaks happen.
3. Service taking `(session, tenant_id)`, building the repo with that tenant_id, committing.
   Look up by id through the scoped repo so another tenant's id is a 404, not a 403.
4. Endpoint using `LearningMember`/`LearningManager` (learning features) or
   `TenantMember`/`TenantManager`, passing `ctx.tenant_id`, never a tenant id
   from the request body or path.
5. Migration (load the `backend-migrations` skill), tests (load `backend-testing`, including a
   cross-tenant-by-id test), a `CHANGES.md` entry.
6. Anything that changes who can do what is an AGENT.md "ask first" decision.

## Gotchas

- Async sessions can't lazy-load. Relationships are `lazy="raise"`; eager-load explicitly. Columns
  set by the DB on UPDATE (`updated_at`) are expired after commit: `await session.refresh(obj)`
  before returning, or set `__mapper_args__ = {"eager_defaults": True}`.
- Enums are stored by value: `Enum(..., values_callable=lambda e: [m.value for m in e])`. Pass enum
  members, not strings (`"USER"` once broke inserts).
- Passwords: `hash_password`/`verify_password` in `core/security.py` (pwdlib/Argon2) only.
- Same error for every auth failure (`Invalid credentials`) so emails/tenants can't be probed.

## Open items (as of 2026-09-26)

- A tenantadmin can remove/demote the last tenantadmin; recovery is a platform invite.
- `frontend/` API types are stale: regenerate with `npm run gen:api` (backend running).
- Email delivery for invites isn't built; the API returns the token once.
- Admin/superviewer accounts: `uv run python -m app.cli create-superadmin <email> --role admin`.
