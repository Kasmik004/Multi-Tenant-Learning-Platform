# Changes

## [2026-09-26] Tests for the IMP_TESTS.md scenarios that weren't covered

- What changed: Added 7 tests and extended 1: tenant accounts can't create tenants; a tenant admin creates only in their own tenant (a body `tenant_id` is ignored, a spoofed header is refused); a learner can't open or report progress on another tenant's course; a cross-tenant user edit leaves the target unchanged; writes without `X-Tenant-Slug` get 400 and create nothing; an expired trial also blocks assignments and progress; an assignment is stored in the right tenant (checked in the DB); a learner can't assign courses or forge progress with extra fields.
- Why: Went through IMP_TESTS.md; the rest of its scenarios were already covered.
- Files: `backend/tests/{test_platform_roles,test_tenant_isolation,test_trial_lifecycle,test_learning}.py`
- Migration: no

## [2026-09-26] CLI can create admin and superviewer accounts

- What changed: `uv run python -m app.cli create-superadmin <email> --role admin|superviewer` (default stays superadmin).
- Why: `admin`/`superviewer` accounts could only be created by a direct DB insert.
- Files: `backend/app/cli.py`
- Migration: no

## [2026-09-26] Course assignment and learning progress

- What changed: New tenant-scoped `enrollments` (course + user, unique; `progress_percent` 0-100 with derived `status` not_started/in_progress/completed and `completed_at`). Tenantadmins assign/unassign and see progress per course (`POST|GET /courses/{id}/enrollments`, `DELETE /courses/{id}/enrollments/{user_id}`); users now see only **published courses assigned to them** (others 404) and read/update their own progress (`GET|PUT /courses/{id}/progress`, `GET /enrollments/me`). All of it requires a running trial. README's stale multi-tenancy section rewritten to match the current design.
- Why: Users saw every course in the tenant, including unpublished ones; AGENT.md requires course assignment and progress.
- Files: `backend/app/models/enrollment.py`, `backend/app/repositories/{base,course,enrollment}.py`, `backend/app/services/{course,enrollment}.py`, `backend/app/schemas/enrollment.py`, `backend/app/api/v1/endpoints/{courses,enrollments}.py`, `backend/app/api/v1/router.py`, `backend/tests/{conftest,test_learning,test_trial_lifecycle}.py`, `README.md`, `docs/tenant-trial.md`
- Migration: yes ([f1a3c5e7b9d2](backend/alembic/versions/20260926_1600_f1a3c5e7b9d2_course_enrollments_and_progress.py)); additive. Existing tenants start with no assignments, so their users see no courses until a tenantadmin assigns some.

## [2026-09-26] Drop deprecated membership columns

- What changed: Dropped `tenant_memberships`, `users.role`, `users.merged_into_id` and the `user_role`/`membership_status` enum types.
- Why: Superseded by per-tenant accounts (a9c3e7f1d2b8) and unused by any code; dropped with user sign-off so the schema matches the models before frontend work.
- Files: none besides the migration
- Migration: yes ([d4f8a2c6e9b1](backend/alembic/versions/20260926_1500_d4f8a2c6e9b1_drop_deprecated_membership_columns.py)); destructive. The downgrade recreates the structure empty; the dropped rows are not recoverable.

## [2026-09-26] Tenant free trial: trial_active -> expired, extend to reactivate

- What changed: New tenants start a `TRIAL_DAYS` (default 14) trial (`tenants.status`, `trial_ends_at`, `expired_at`). Once `trial_ends_at` passes, every `/courses` call and every invite returns 403 `trial_expired` (checked per request via `LearningMember`/`LearningManager`/`TenantInviter`); sign-in, `/auth/me`, `/tenants/current` and user management keep working and no data is touched. `uv run python -m app.cli expire-trials` records expiries with one conditional UPDATE (idempotent, safe to run concurrently). Superadmin/admin reactivate or extend via `POST /tenants/{slug}/trial {days}` (adds to a running trial, restarts an expired one from now). Documented in `docs/tenant-trial.md`.
- Why: Tenants get a free trial; learning features must stop when it ends without deleting anything, and the platform needs a way to restore access (no payments yet).
- Files: `backend/app/models/tenant.py`, `backend/app/services/tenant.py`, `backend/app/api/deps.py`, `backend/app/api/v1/endpoints/{courses,tenants}.py`, `backend/app/schemas/tenant.py`, `backend/app/core/{config,exceptions}.py`, `backend/app/cli.py`, `backend/tests/{conftest,test_trial_lifecycle}.py`, `docs/tenant-trial.md`
- Migration: yes ([b7d2e4f6a1c3](backend/alembic/versions/20260926_1400_b7d2e4f6a1c3_tenant_trial_lifecycle.py)); additive; existing tenants get a fresh 14-day trial from the time it runs.

## [2026-09-26] Claude Code skills for the backend

- What changed: Added `.claude/skills/` with `backend-architecture` (tenancy, auth, roles, layering, feature checklist), `backend-migrations` (rules, revision chain, `check_migrations.py` round-trip/drift script) and `backend-testing` (fixtures, isolation test pattern).
- Why: So new sessions know how to work on the backend without re-deriving it.
- Files: `.claude/skills/*`
- Migration: no

## [2026-09-26] Platform roles limited to tenant metadata; they invite only tenantadmins

- What changed: Superadmin/admin can only invite `tenantadmin`s; only a tenantadmin can invite `user`s. No platform role (superviewer included) can list/edit/remove a tenant's users or read/write its courses. They keep tenant metadata (`/tenants`, `/tenants/current`).
- Why: Protect users' PII and keep each tenant's data inside the tenant.
- Files: `backend/app/api/deps.py`, `backend/app/api/v1/endpoints/{users,tenants}.py`, `backend/tests/test_platform_roles.py`
- Migration: no

## [2026-09-26] Per-tenant accounts joined by admin invite

- What changed: Each account belongs to one tenant (`users.tenant_id` + `tenant_role`; same email may have separate accounts per tenant). Tenant managers invite users via `POST /users/invites` (single-use, hashed, 72h token); users redeem it at `POST /auth/accept-invite` with their own password. Self-register, join requests and `/memberships` are removed; login takes an optional `tenant_slug` (omit for platform accounts).
- Why: Tenants are separate organizations: users must not browse tenants or reach another tenant's data, and are onboarded by their tenant admin.
- Files: `backend/app/models/user.py`, `backend/app/api/deps.py`, `backend/app/services/{auth,user}.py`, `backend/app/api/v1/endpoints/{auth,users,tenants}.py`, `backend/app/repositories/user.py`, `backend/tests/*`
- Migration: yes ([a9c3e7f1d2b8](backend/alembic/versions/20260926_1000_a9c3e7f1d2b8_per_tenant_users_with_invites.py)); additive, un-merges accounts; `tenant_memberships`, `users.role`, `users.merged_into_id` are deprecated pending a destructive migration.

## [2026-09-26] Fix e5d1a7b3c9f4 downgrade granting tenant access from pending join requests

- What changed: The downgrade backfills `users.tenant_id`/`role` only from `active` memberships.
- Why: It picked the oldest membership of any status, so a user with only a pending join request became a tenant member after downgrading.
- Files: `backend/alembic/versions/20260925_1300_e5d1a7b3c9f4_global_users_and_tenant_memberships.py`
- Migration: no (fixes an existing migration's downgrade)

## [2026-09-25] Multi-tenant users: tenant via X-Tenant-Slug header, roles split platform/tenant

- What changed: Users are global accounts; tenant access lives in `tenant_memberships` (role `tenantadmin`/`user`, status `pending`/`active`/`rejected`), and platform roles (`superadmin`/`admin`/`superviewer`) live on `users.platform_role`. The JWT carries only `sub`; tenant-scoped routes read `X-Tenant-Slug` and check an active membership on every request (platform roles bypass it; superviewer is read-only). Users self-register without a tenant, request to join via `POST /tenants/{slug}/join-requests`, and a tenantadmin approves/rejects/changes role/removes via `/memberships`. Only superadmin creates/deletes tenants; admin can update them. `POST /tenants` is no longer open, `/users` endpoints are replaced by `/memberships`, login/register no longer take `tenant_slug`. First superadmin: `uv run python -m app.cli create-superadmin <email>`.
- Why: A user must be able to belong to several tenants at once, which the token-embedded tenant and per-tenant user rows couldn't express; roles laid out per the platform/tenant permission list.
- Files: `backend/app/api/deps.py`, `backend/app/models/{user,membership}.py`, `backend/app/repositories/{user,membership}.py`, `backend/app/services/{auth,tenant,membership}.py`, `backend/app/api/v1/endpoints/{auth,tenants,memberships,courses}.py`, `backend/app/core/security.py`, `backend/app/cli.py`, `backend/tests/*`
- Migration: yes ([e5d1a7b3c9f4](backend/alembic/versions/20260925_1300_e5d1a7b3c9f4_global_users_and_tenant_memberships.py)) — additive only: duplicate per-tenant accounts are merged into the oldest one by email (`merged_into_id`), old `users.tenant_id`/`users.role` become nullable and are kept until a follow-up destructive migration.

## [2026-09-25] Fix registered users being unable to log in

- What changed: `AuthService.register` hashes with `hash_password` from `core/security.py`; the ad-hoc bcrypt `HashService` was removed.
- Why: Login returned 500 (`pwdlib UnknownHashError`) for self-registered users because `register()` hashed passwords with raw bcrypt while `login()` verifies with pwdlib's recommended (Argon2-only) hasher, which can't identify bcrypt hashes. `HashService` also reused one module-level salt for every password.
- Files: `backend/app/services/auth.py`, `backend/tests/test_auth_and_tenants.py`
- Migration: no

## [2026-09-25] Fix registration failing on NULL full_name / tenant_id and never persisting

- What changed: `users.full_name` is now nullable; `UserRepository.create` goes through `add()` so `tenant_id` is set; `AuthService.register` now commits.
- Why: Registration failed with a NOT NULL violation because `RegisterRequest` has no full name and `UserRepository.create` added the user to the session directly, skipping the `add()` override that stamps `tenant_id`. Once that passed, the user was still rolled back because `register()` never called `commit()` (services own transactions).
- Files: `backend/app/models/user.py`, `backend/app/schemas/user.py`, `backend/app/repositories/user.py`, `backend/app/services/auth.py`, `backend/tests/test_auth_and_tenants.py`
- Migration: yes ([c4a8f2e61b90](backend/alembic/versions/20260925_1210_c4a8f2e61b90_make_user_full_name_nullable.py))

## [2026-09-25] Fix registration failing with invalid `user_role` enum value

- What changed: `AuthService.register` passes `UserRole.USER` instead of the string `"USER"`; the `user_role` DB enum gains `superadmin`, `superviewer`, `tenantadmin`, `user`.
- Why: Registration failed with `invalid input value for enum user_role: "USER"`. The service passed the raw uppercase string, which bypasses the enum's lowercase value mapping, and the DB type still only had the old `admin`/`instructor`/`learner` values after the `UserRole` rename.
- Files: `backend/app/services/auth.py`, `backend/tests/test_auth_and_tenants.py`
- Migration: yes ([7b3e9c1a4d2f](backend/alembic/versions/20260925_1200_7b3e9c1a4d2f_add_new_user_roles.py))
