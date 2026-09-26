# Design notes

This is a short tour of how the system is put together and why. If you want to run it, read the [README](README.md) instead. If you want every change in order, see [CHANGES.md](CHANGES.md).

## The problem

Several organizations need a place to run training for their people. Each one wants its own admins, its own learners and its own courses. None of them should ever see another's data, even by accident.

That last sentence drove most of the decisions below. Features are the easy part. Keeping tenants apart is the part that has to be right every time.

## The shape of it

Three pieces:

```
Next.js frontend  ──▶  FastAPI backend  ──▶  PostgreSQL
  (port 3000)            (port 8000)
```

Nothing fancy. No message queue, no cache, no microservices. A learning platform for a handful of organizations doesn't need them, and every extra moving part is one more thing to deploy and debug. If it grows, the backend is stateless, so running more copies behind a load balancer is the first step, and it's cheap.

The backend is async Python (FastAPI and SQLAlchemy). The frontend is mostly client-side React. It logs in, keeps the token, and shows one of three dashboards depending on who you are: platform staff, tenant admin, or learner.

## One database, one set of tables

Every tenant lives in the same tables. Rows that belong to a tenant carry a `tenant_id`. The step-by-step version is in [docs/tenant-isolation-and-expiry.md](docs/tenant-isolation-and-expiry.md).

We looked at giving each tenant its own schema or its own database. That buys stronger walls, but you pay for it on every migration and every new customer. For many small tenants, shared tables are the sane default. A big customer could still be moved to its own database later without changing the API.

The catch with shared tables is that one forgotten `WHERE tenant_id = ...` leaks data. So we didn't leave it to memory:

- Repositories for tenant data are built with a tenant id and apply the filter themselves, on every read and every insert. Service code can't "forget", because it never writes that filter by hand.
- The client never gets to choose the tenant id. It sends a tenant slug in a header, and the server checks on every request that the logged-in account belongs to that tenant. Anything in the request body called `tenant_id` is ignored.
- A wrong tenant and a tenant that doesn't exist return the same error. You can't use the API to discover which organizations are on the platform.
- There are tests whose whole job is to try reaching another tenant's data and fail.

## Layers in the backend

```
endpoints  →  services  →  repositories  →  models
```

Endpoints handle HTTP and permissions. Services hold the rules and decide when to commit. Repositories are the only place that talks to the database. It's a common pattern and a bit more ceremony than a demo strictly needs, but it keeps the permission logic in one file (`api/deps.py`) where it's easy to review.

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

More detail in [docs/tenant-trial.md](docs/tenant-trial.md).

## Keeping frontend and backend in sync

The frontend's API types are generated from the backend's OpenAPI description. Rename a field in the backend, regenerate, and the frontend stops compiling until you fix it. A build error is annoying. A silent runtime bug in front of a user is worse.

## Changing the database safely

Every schema change is an Alembic migration. They have to be reversible, and we never add and remove things in the same step. When we moved to per-tenant accounts, the old columns were first left in place and only dropped in a later migration, once nothing used them. [AGENT.md](AGENT.md) has the full rules.

## Testing

Tests run against a real PostgreSQL database, not mocks or SQLite. Most of the bugs worth catching here are about queries, constraints and enum types, and a fake database would happily hide them. We didn't chase coverage. The tests go after what would hurt: sign-in, role permissions, tenant isolation, trial expiry, course assignment and progress.

## What's missing, honestly

- **No email.** Invite tokens are shown on screen and passed along by hand.
- **No payments.** A trial is extended by a platform admin, not by a customer paying.
- **The browser keeps the login token in `localStorage`.** It's simple, but a cross-site scripting bug could read it. An httpOnly cookie would be the next step for a real deployment.
- **No refresh tokens.** You log in again after 60 minutes.
- **Courses are just a title and description.** Lessons, content and quizzes would be the next feature, and adding them follows the same tenant-scoped pattern as everything else.

None of these change the core design. They're next steps, not rewrites.
