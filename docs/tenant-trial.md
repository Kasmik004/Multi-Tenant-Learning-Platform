# Tenant free trial

Every new organization (tenant) gets a free trial. When the trial ends, its people can still sign
in, but the learning features are switched off until the platform team extends the trial. Nothing
is deleted. There are no payments or subscriptions yet; extending the trial is how a tenant gets
access back.

## The three stages

```
Created ──(immediately)──▶ Trial active ──(end date passes)──▶ Expired
                                ▲                                  │
                                └────── platform extends trial ────┘
```

| Stage | What it means | Stored as |
|---|---|---|
| Created | The superadmin has just created the tenant. | Nothing extra; the trial starts in the same step. |
| Trial active | Everything works. | `status = trial_active`, `trial_ends_at` in the future |
| Expired | Learning features are blocked. | `trial_ends_at` in the past; `status = expired` once recorded (below) |

`GET /tenants/current` (and the platform's `GET /tenants/{slug}`) shows `status`,
`trial_ends_at` and `expired_at`, so the app can tell members when their trial ends or why
access is limited.

## 1. How the trial period is calculated

- Trial end = the moment the tenant is created + `TRIAL_DAYS` (a setting, default **14 days**).
- All times are stored in UTC, down to the second. A tenant created on 1 March at 09:30 UTC keeps
  full access until 15 March at 09:30 UTC.
- Tenants that existed before this feature shipped got a full 14-day trial starting from the
  moment the database update ran, so no one lost access on the day of release.

## 2. How expiration is detected and processed

Two things work together:

1. **Every request checks the date.** Before any learning feature runs, the server compares the
   tenant's trial end with the current time. If the end has passed, the request is refused,
   even if nothing else has happened yet. Access therefore stops on time, whether or not any
   background job has run.
2. **A cleanup command records it.** `uv run python -m app.cli expire-trials` (run it on a
   schedule, e.g. hourly) marks every tenant whose trial has ended as `expired` and saves when
   that was noticed (`expired_at`). It also logs each tenant it expired, so emails or reports
   can hook in there later. This record is for reporting and for the platform team. Access
   control doesn't depend on it.

A tenant that the platform **deactivates** (`is_active = false`) is a separate, stronger lock:
its members can't sign in at all. Trial expiry is softer on purpose (see below).

## 3. What happens to existing users and data

Nothing is deleted or changed. Courses, users, course assignments, learners' progress and
pending invites all stay as they were.

| Once expired | Allowed? |
|---|---|
| Sign in, see own profile (`/auth/me`) | ✅ |
| See the tenant's status and trial dates (`/tenants/current`) | ✅ |
| Tenant admins: list users, change a user's role, remove a user | ✅ |
| Accept an invite sent before the trial ended | ✅ (they join, then see the same limits) |
| View courses (list or single) | ❌ |
| Create, edit or delete courses | ❌ |
| Assign or unassign courses, see who's assigned | ❌ |
| View or update own progress (`/courses/{id}/progress`, `/enrollments/me`) | ❌ |
| Send new invites (tenant admins and platform admins alike) | ❌ |

Blocked requests get **HTTP 403** with the error code `trial_expired` (not the general
`forbidden`), so the app can show a clear "your trial has ended" message instead of a
permissions error. Any learning feature added later (enrollment, progress) should use the same
check: the `LearningMember` / `LearningManager` permissions in `backend/app/api/deps.py`.

## 4. How a tenant is reactivated

A platform **superadmin** or **admin** calls:

```
POST /api/v1/tenants/{slug}/trial
{"days": 30}        # 1 to 365
```

- **Expired tenant:** the new trial runs `days` from *now*. Its status goes back to
  `trial_active`, `expired_at` is cleared, and everyone's access returns at once with all
  their data.
- **Tenant still in trial:** `days` are *added* to the current end date. Extending never
  shortens a trial.

Tenant admins, regular users and superviewers can't extend trials.

## 5. Running the expiry processing more than once

The cleanup command is safe to run as often as you like, and even as two copies at once:

- It changes only tenants that are still marked `trial_active` **and** whose end date has
  passed, in a single database update. A tenant that is already `expired` is never touched
  again, so its `expired_at` keeps the time it was first recorded and it is logged only once.
- If two copies run at the same moment, the database lets only one of them change each tenant;
  the other finds nothing left to do.
- If a tenant is reactivated while the command runs, its new end date is in the future, so it
  no longer matches and isn't expired again.
- If the command never runs (or a run is missed), members are still blocked on time by the
  per-request check. Only the `expired_at` record is late.

## Where it lives in the code

| Piece | File |
|---|---|
| Stages, dates, "is it over?" check | `backend/app/models/tenant.py` |
| Start, extend, cleanup logic | `backend/app/services/tenant.py` |
| Which endpoints are blocked | `backend/app/api/deps.py`, `backend/app/api/v1/endpoints/{courses,enrollments}.py` |
| Extend endpoint | `backend/app/api/v1/endpoints/tenants.py` |
| Cleanup command | `backend/app/cli.py` (`expire-trials`) |
| Database change | `backend/alembic/versions/20260926_1400_b7d2e4f6a1c3_tenant_trial_lifecycle.py` |
| Tests | `backend/tests/test_trial_lifecycle.py` |
