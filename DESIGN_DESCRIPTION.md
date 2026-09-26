# Design notes

## The problem

Several organizations need a place to run training for their people. Each one wants its own admins, its own learners and its own courses. None of them should ever see another's data, even by accident.

## The shape of it

Three pieces:

```
Next.js frontend  ──▶  FastAPI backend  ──▶  PostgreSQL
  (port 3000)            (port 8000)
```

The system is kept minimal: no message queue, no cache, no microservices. A learning platform for a handful of organizations doesn't need them. If it grows, the backend is stateless, so running more copies behind a load balancer is the first step, and it's cheap.

The backend is async Python (FastAPI and SQLAlchemy). The frontend is mostly client-side React. It logs in, keeps the token, and shows one of three dashboards depending on who you are: platform staff, tenant admin, or learner.

## One database, one set of tables

Every tenant lives in the same tables. Rows that belong to a tenant carry a `tenant_id`.

Giving each tenant its own schema or its own database provides stronger walls, but it gets tedious with every migration and every new customer. For many small tenants, shared tables are the sane default. A big customer could still be moved to its own database later without changing the API.

The catch with shared tables is that one forgotten `WHERE tenant_id = ...` leaks data. So we didn't leave it to memory:

- Repositories for tenant data are built with a tenant id and apply the filter themselves, on every read and every insert. Service code can't "forget", because it never writes that filter by hand.
- The client never gets to choose the tenant id. It sends a tenant slug in a header, and the server checks on every request that the logged-in account belongs to that tenant. Anything in the request body called `tenant_id` is ignored.
- A wrong tenant and a tenant that doesn't exist return the same error. You can't use the API to discover which organizations are on the platform.
- There are tests whose whole job is to try reaching another tenant's data and fail.

### One request, step by step

Jane is a learner at Acme. She opens her course list.

1. Her browser sends her login token and the header `X-Tenant-Slug: acme`.
2. The server reads the token and loads Jane's account. If the account was removed, she is stopped here.
3. The server checks that Jane's account belongs to `acme`. It does, so she goes on.
4. The server makes a data reader locked to Acme. Every query it runs only sees Acme's rows.
5. Jane is a learner, so she only gets courses that are published and assigned to her.

### What if someone tries to cheat?

| Attempt | Result |
| --- | --- |
| Change the header to another tenant | 403 |
| Use a made-up tenant name | The same 403 |
| Ask for another tenant's course by its id | 404, as if it doesn't exist |
| Put a `tenant_id` in the request body | Ignored |
| Leave out the tenant header | 400 |
| Admin edits or deletes a user from another tenant | 404, and that user is not changed |
| Admin assigns a course to a user from another tenant | 404 |

Code: `repositories/base.py` (the locked reader) and `api/deps.py` (the tenant check). Tests: `tests/test_tenant_isolation.py` and `tests/test_learning.py`.

## Layers in the backend

```
endpoints  →  services  →  repositories  →  models
```

Endpoints handle HTTP and permissions. Services hold the rules and decide when to commit. Repositories are the only place that talks to the database. It's a common pattern and keeps the permission logic in one file (`api/deps.py`) where it's easy to review.

## Who can do what

There are two families of accounts, and we kept them separate on purpose.

**Platform staff** (superadmin, admin, superviewer) run the platform. They can create tenants, extend trials and look at tenant metadata. They can't read a tenant's users or courses. That was a deliberate call. The people running the service don't need learners' personal data to do their job, so they don't get it.

**Tenant accounts** (tenantadmin, user) belong to exactly one organization. Admins manage people and courses. Users learn.

## Accounts and sign-in

This part changed the most, and it's worth saying why.

The first version had global accounts. One login, and you could join several tenants through membership requests. It sounded flexible. In practice it let users browse tenants they didn't belong to, and it made "which tenant am I acting in right now?" a question every endpoint had to answer carefully. We replaced it with **one account per tenant**. The same email can exist in two organizations as two separate accounts, with separate passwords. Less clever, and much easier to reason about.

Other choices:

- **Invite-only.** No public sign-up. An admin invites you, you get a single-use token (72 hours, stored only as a hash), you set a password. Organizations are private, so this felt right.
- **The login token only says who you are.** It holds a user id and an expiry, nothing about roles or tenants. The server loads the user on each request, so removing someone or changing their role takes effect straight away instead of when the token expires.
- **Passwords** are hashed with Argon2.

## The free trial

Every new tenant gets 14 days. After that, learning features stop but nothing is deleted. People can still log in, and admins can still manage users. A platform admin can extend the trial and everything comes back as it was.

The interesting bit is *when* expiry happens. We check the end date on every request, so access stops on time, full stop. There's also a scheduled command that marks tenants as expired, but that's only bookkeeping for reports. If the job doesn't run for a day, nobody gets extra access. The command is also safe to run twice, or twice at once.

Expired tenants get a specific `trial_expired` error rather than a generic "forbidden", so the frontend can say what actually happened.

```
create tenant ──▶ trial active ──(end date passes)──▶ expired
                       ▲                                 │
                       └───── platform extends trial ────┘
```

### How the trial period is calculated

The trial starts when the tenant is created.

```
trial end = creation time + TRIAL_DAYS
```

`TRIAL_DAYS` is a setting. It is 14 by default. Times are saved in UTC. A tenant created on 1 March at 09:30 UTC can use everything until 15 March at 09:30 UTC.

### How expiration is detected and processed

There are two parts.

1. **A check on every request.** Before any learning feature runs, the server compares the trial end with the current time. If the trial is over, the request gets a 403 with the code `trial_expired`. This check alone controls access.
2. **A cleanup command.** `uv run python -m app.cli expire-trials` should run on a schedule, for example every hour. It marks ended trials as `expired`, saves the time in `expired_at`, and writes a log line for each one. This is only for records. If it runs late, nobody gets extra access.

### What happens to existing users and data

Nothing is deleted. Courses, users, assignments, progress and invites all stay. Some of it is just paused.

| After expiry | Allowed? |
| --- | --- |
| Log in and see your profile | Yes |
| See the tenant's status and trial dates | Yes |
| Admin: list, change or remove users | Yes |
| View courses | No |
| Create, edit or delete courses | No |
| Assign or unassign courses | No |
| View or update progress | No |
| Send new invites | No |

Login keeps working so people see "your trial has ended" instead of a broken login.

This is softer than turning a tenant off. A platform admin can set `is_active = false`, and then nobody from that tenant can log in at all.

### How a tenant is reactivated

A platform superadmin or admin calls:

```
POST /api/v1/tenants/{slug}/trial
{"days": 30}
```

`days` can be 1 to 365.

- If the trial has **expired**, the new trial runs 30 days from now. The status goes back to `trial_active` and `expired_at` is cleared. All courses and progress come back at once.
- If the trial is **still running**, the 30 days are added to the current end date. A trial is never made shorter.

Tenant admins, learners and superviewers cannot extend trials.

### How repeated expiration processing is handled

The cleanup command does its work in one database statement:

```sql
UPDATE tenants
SET status = 'expired', expired_at = now
WHERE status = 'trial_active' AND trial_ends_at <= now
```

Because of this:

- A tenant that is already `expired` is skipped. It is marked and logged only once, and `expired_at` keeps the first time.
- If two copies run at the same moment, the database lets only one change each tenant. The other finds nothing to do.
- A tenant that was just reactivated has a future end date, so it is not expired again.
- A missed run does not matter for access, because the per-request check already blocked people on time.

Code: `models/tenant.py`, `services/tenant.py` and `cli.py`. Tests: `tests/test_trial_lifecycle.py`.

More detail in [docs/tenant-trial.md](docs/tenant-trial.md).

## Keeping frontend and backend in sync

The frontend's API types are generated from the backend's OpenAPI description. Rename a field in the backend, regenerate, and the frontend stops compiling until you fix it. A build error is annoying. A silent runtime bug in front of a user is worse.

## Changing the database safely

Every schema change is an Alembic migration. They have to be reversible, and we never add and remove things in the same step. When we moved to per-tenant accounts, the old columns were first left in place and only dropped in a later migration, once nothing used them. [AGENT.md](AGENT.md) has the full rules.

## Testing

Tests run against a real PostgreSQL database, not mocks or SQLite. Most of the bugs worth catching here are about queries, constraints and enum types, and a fake database would happily hide them. The tests go after what matters most: sign-in, role permissions, tenant isolation, trial expiry, course assignment and progress.

## What's missing, honestly

- **No email.** Invite tokens are shown on screen and passed along by hand.
- **No payments.** A trial is extended by a platform admin, not by a customer paying.
- **The browser keeps the login token in `localStorage`.** It's simple, but a cross-site scripting bug could read it. An httpOnly cookie would be the next step for a real deployment.
- **No refresh tokens.** You log in again after 60 minutes.
- **Courses are just a title and description.**

## Other design decisions

At first, when an admin created a new learner, the backend would have told the admin if the learner was already in another tenant, because we couldn't have duplicate emails. But I realized that this would have leaked the learner's information: an admin could find out that the person belongs to another organization. So I allowed the same email to be stored more than once in the database (once per tenant) to avoid this issue.

## How this project was built

This project was developed with the help of an AI agent, so I created an AGENT.md at the start and refined it over time so that the agent would stay on track and perform as desired, without trying to be unnecessarily creative. In AGENT.md, the agent was instructed to maintain a CHANGES.md that logs every change the agent makes. This helped me keep track of everything the agent had done, and it also helped the agent understand previous work and context.

Relevant and useful skills were downloaded from an online skills library and provided to the agent inside the `.claude` folder. I also created a new skill for each specific workflow that I wanted the agent to follow across different agent sessions, so that I didn't need to re-explain everything.

Also, if there was a specific instruction, or context that kept repeating, that I wanted the agent to have access to, I kept it in a markdown file in the `docs` folder. That made it easier for the agent to know what to do and how things actually work in the system.

And I used Graphify to give the agent the codebase information, so that it would use fewer tokens.
