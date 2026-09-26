# Tenant isolation and trial expiry

This page explains two things: how we keep each organization's data away from the others, and what happens when an organization's free trial runs out.

Quick vocabulary. An organization on the platform is a **tenant**. Each tenant has a short name called a **slug**, like `acme`. That's all the jargon you need.

---

## Part 1: Keeping tenants apart

### The setup

All tenants share one database and the same tables. Acme's courses and Globex's courses sit side by side in the `courses` table. What tells them apart is a `tenant_id` column on every row.

We chose this because it's simple to run: one database, one set of migrations, and adding a tenant is just adding a row. The price is that the code has to be careful. One query that forgets to filter by tenant, and Acme could see Globex's courses.

So we made the careful part automatic. Here's how.

### Walkthrough: Jane opens her course list

Jane is a learner at Acme. She clicks "My courses".

**1. The browser sends two things.** Her login token, which only says "this is user 42", and a header saying which tenant she wants: `X-Tenant-Slug: acme`.

**2. The server checks who she is.** It reads the token and loads Jane's account from the database. If the account was deleted or disabled, she's rejected right here, even if her token hasn't expired yet.

**3. The server checks she belongs to that tenant.** It looks up `acme` and compares it to the tenant on Jane's account. They match, so she's in.

If Jane had changed the header to `globex`, the check would fail and she'd get a 403. She'd get the *same* 403 for a made-up slug like `xyz`. That's on purpose: you can't use error messages to find out which organizations exist.

**4. The server builds a "tenant-locked" data reader.** Before any database work, the code creates a repository that is fixed to Acme's tenant id. Every query that repository runs gets `WHERE tenant_id = <acme>` added automatically. Every row it saves gets Acme's tenant id stamped on it. The code that asks for "all courses" never writes the tenant filter itself, so it can't forget it.

**5. Extra rules on top.** Jane is a learner, so she only sees courses that are published *and* assigned to her. That's a normal business rule, and it runs inside Acme's data only.

**6. She gets her list.** Only Acme rows, only hers.

### What if someone tries to cheat?

| Attempt | What happens |
| --- | --- |
| Change the `X-Tenant-Slug` header to another tenant | 403. The account doesn't belong there. |
| Guess the id of another tenant's course and request it directly | 404. The locked reader simply can't find it, so it looks like the course doesn't exist. |
| Send `"tenant_id": "<globex id>"` inside a request body | Ignored. The tenant only ever comes from the checked header, never from the body. |
| Leave out the tenant header | 400. Tenant pages won't run without knowing the tenant. |
| An Acme admin tries to edit or delete a Globex user by id | 404, and the Globex user is untouched. |
| An Acme admin tries to assign a course to a Globex user | 404. Both the course and the user have to be in the admin's own tenant. |

### Accounts belong to one tenant

Every tenant account belongs to exactly one tenant. The same email can have separate accounts at Acme and at Globex, each with its own password, and they know nothing about each other. When you log in, you give the tenant slug, and the server looks for your email *inside that tenant only*.

People who run the platform (superadmin, admin, superviewer) have accounts that belong to no tenant. They can see tenant details like name, status and trial dates, but not a tenant's users or courses. The people running the service don't need learners' personal data, so they don't get it.

### How we know it works

There are tests that do exactly the cheating in the table above and expect to be refused. They're in `backend/tests/test_tenant_isolation.py` and `backend/tests/test_learning.py`, and they run on every push.

### Where to look in the code

| What | File |
| --- | --- |
| The tenant-locked repository | `backend/app/repositories/base.py` (`TenantScopedRepository`) |
| The "do you belong to this tenant?" check | `backend/app/api/deps.py` (`get_tenant_context`) |
| Login scoped to one tenant | `backend/app/services/auth.py` |

---

## Part 2: Trial expiry

Every new tenant starts on a free trial. When it ends, learning features switch off until the platform team extends it. There are no payments yet, so extending the trial is how a tenant gets access back.

### How is the trial period calculated?

When a superadmin creates a tenant, the trial starts in the same step:

```
trial end = moment the tenant was created + TRIAL_DAYS
```

`TRIAL_DAYS` is a setting, and it defaults to 14. Times are stored in UTC, to the second. A tenant created on 1 March at 09:30 UTC has full access until 15 March at 09:30 UTC.

### How is expiry detected and processed?

Two things happen, and only the first one controls access.

**The check on every request.** Before any learning feature runs, the server compares the tenant's trial end with the current time. If the end has passed, the request is refused with a 403 and the error code `trial_expired`. No background job is needed for this. Access stops on time.

**The cleanup command.** This one is for record-keeping:

```bash
uv run python -m app.cli expire-trials
```

Run it on a schedule, say hourly. It finds tenants whose trial has ended, marks them `expired`, and records when (`expired_at`). It also logs each one, which is where emails or reports could plug in later. If the command is late or never runs, nobody gets extra access. Only the record is late.

```
  create tenant ──▶ trial active ──(end date passes)──▶ expired
                          ▲                                │
                          └──── platform extends trial ────┘
```

### What happens to existing users and data?

Nothing is deleted or changed. Courses, users, assignments, progress and pending invites all stay exactly as they were. Access to some of it just pauses.

| After expiry | Allowed? |
| --- | --- |
| Log in and see your own profile | Yes |
| See the tenant's status and trial dates | Yes |
| Tenant admin: list users, change roles, remove users | Yes |
| View courses | No |
| Create, edit or delete courses | No |
| Assign or unassign courses | No |
| View or update your progress | No |
| Send new invites | No |

We kept login working on purpose. A user whose trial ended should see "your trial has ended", not a mysterious login failure. That's also why the error code is `trial_expired` and not a generic "forbidden".

This is softer than deactivating a tenant. A platform admin can switch a tenant off completely (`is_active = false`), and then nobody from that tenant can log in at all.

### How can a tenant be reactivated?

A platform superadmin or admin extends the trial:

```
POST /api/v1/tenants/acme/trial
{"days": 30}
```

`days` must be between 1 and 365.

- **Expired tenant:** the new trial runs 30 days *from now*, not from the old end date. The status goes back to `trial_active` and `expired_at` is cleared. Everyone's courses and progress come back at once, because nothing was removed.
- **Tenant still on its trial:** the 30 days are *added* to the current end date. Extending never shortens a trial.

Tenant admins, learners and superviewers can't extend trials.

### How do we handle repeated expiry processing?

The cleanup command is safe to run as often as you like, even as two copies at the same moment. It does all its work in one database statement, roughly:

```sql
UPDATE tenants
SET status = 'expired', expired_at = now
WHERE status = 'trial_active' AND trial_ends_at <= now
```

What that gets us:

- **Already expired tenants are skipped.** The `status = 'trial_active'` condition means a tenant is marked once. Its `expired_at` keeps the time it was first recorded, and it's logged only once.
- **Two copies at once don't clash.** The database lets only one of them change each row. The second finds nothing left to do.
- **A tenant reactivated mid-run isn't expired again.** Its new end date is in the future, so it no longer matches.
- **A missed run doesn't matter for access.** The per-request check already blocked people on time.

### Where to look in the code

| What | File |
| --- | --- |
| Trial dates and the "is it over?" check | `backend/app/models/tenant.py` |
| Start, extend and cleanup logic | `backend/app/services/tenant.py` |
| Which endpoints need a running trial | `backend/app/api/deps.py` (`LearningMember`, `LearningManager`, `TenantInviter`) |
| The cleanup command | `backend/app/cli.py` (`expire-trials`) |
| Tests | `backend/tests/test_trial_lifecycle.py` |
