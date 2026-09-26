# Learning Platform

A web app where organizations (schools, training institutes, companies) run their own private learning space. Each organization gets its own admins, its own learners and its own courses, and none of them can see another organization's data.

In the code, an organization is called a **tenant**. One running copy of the app serves many tenants at once. This setup is usually called "multi-tenant".

It's a demo project, but the backend is built to production standards: real database migrations, tests against a real database, and access checks on every request.

## What you can do with it

There are two kinds of accounts.

**Platform accounts** belong to the team running the app, not to any organization:

| Role | Can do |
| --- | --- |
| `superadmin` | Create and delete tenants, invite a tenant's first admin, extend trials |
| `admin` | Edit tenants, invite tenant admins, extend trials |
| `superviewer` | Look at the list of tenants, read-only |

Platform accounts only see *information about* tenants (name, status, trial dates). They can't see a tenant's users or courses. We chose this to keep people's personal data inside their own organization.

**Tenant accounts** belong to one organization:

| Role | Can do |
| --- | --- |
| `tenantadmin` | Invite users, manage users, create courses, assign courses to users, see everyone's progress |
| `user` | See the courses assigned to them and report how far they've got (0 to 100%) |

A typical flow:

1. A superadmin creates a tenant, say "Acme Academy", and invites its first tenant admin.
2. The tenant admin accepts the invite, sets a password, and invites learners.
3. The tenant admin creates courses, publishes them and assigns them to learners.
4. Learners log in, see only their assigned courses, and update their progress.
5. The tenant admin watches progress per course.

Every new tenant gets a 14-day free trial. When it ends, people can still log in, but courses, progress and new invites are switched off until a platform admin extends the trial. Nothing gets deleted. [docs/tenant-trial.md](docs/tenant-trial.md) has the details.

## How it's built

For the reasoning behind the design, see [DESIGN.md](DESIGN.md).

```
  Browser
     │
     ▼
┌──────────────┐    HTTP + JSON     ┌──────────────┐      SQL      ┌──────────────┐
│   Frontend   │ ─────────────────▶ │   Backend    │ ────────────▶ │  PostgreSQL  │
│   Next.js    │   login token +    │   FastAPI    │               │   database   │
│  port 3000   │   tenant name      │  port 8000   │               │  port 5432   │
└──────────────┘                    └──────────────┘               └──────────────┘
```

| Part | Tools |
| --- | --- |
| Backend (`backend/`) | Python 3.12, FastAPI, SQLAlchemy (talks to the database), Alembic (database changes), uv (package manager) |
| Frontend (`frontend/`) | Next.js 16, React 19, TypeScript, Tailwind CSS |
| Database | PostgreSQL 17 |
| Running it all | Docker Compose |
| CI | GitHub Actions runs linting, type checks, migrations and tests on every push |

### Backend layers

A request passes through four layers, and each one has a single job:

```
endpoints/     receives the HTTP request, checks who you are and what you're allowed to do
   │
services/      the actual rules ("a learner can only see assigned, published courses")
   │           and it decides when to save to the database
repositories/  reads and writes database rows
   │
models/        the table definitions
```

Keeping these separate means the permission checks live in one file (`backend/app/api/deps.py`), the business rules live in services, and nothing outside the repositories writes SQL.

### How tenants are kept apart

All tenants share one database and the same tables. Every row that belongs to a tenant has a `tenant_id` column saying whose it is.

The alternative is a separate database per tenant. That gives stronger walls but is much more work to run: every new tenant means a new database, and every schema change has to be applied N times. For a platform with many small organizations, shared tables are simpler, and the design can still move a big customer to its own database later without changing the API.

The risk with shared tables is obvious: forget one `WHERE tenant_id = ...` and one tenant sees another's data. So the code doesn't rely on people remembering it:

- Repositories for tenant data are created *with* a tenant id, and they add the tenant filter to every query and stamp it on every new row automatically.
- The browser never gets to pick the tenant id. The login token only says who you are. The tenant comes from an `X-Tenant-Slug` header, and the server checks on every request that your account actually belongs to that tenant. A tenant that doesn't exist and a tenant that isn't yours give the same error, so the tenant's name don't get leaked.
- Tests (`tests/test_tenant_isolation.py`, `tests/test_learning.py`) try to list, read, edit and delete another tenant's data and expect to be refused.

### Other decisions and why

- **Invite-only sign-up.** There's no public registration page. Admins invite people. Organizations are private, so strangers shouldn't be able to create accounts or look around. Invite tokens are single-use, expire after 72 hours, and only a hash of them is stored.
- **One account per tenant.** The same email can have separate accounts in two organizations, with separate passwords. An earlier version had one global account that joined several tenants. We dropped it because it let users browse tenants and made it harder to keep data apart (the history is in [CHANGES.md](CHANGES.md)).
- **Trial expiry is checked on every request.** A scheduled command also marks expired tenants, but only for record-keeping. If the job doesn't run, access still stops on time.
- **Soft block when a trial ends.** Users can log in and admins can manage users, but learning features return a `trial_expired` error. The app can show "your trial has ended" instead of a confusing "forbidden".
- **Frontend types come from the backend.** `frontend/src/types/api.d.ts` is generated from the backend's API description. If the backend changes a field, the frontend fails to compile instead of breaking at runtime.
- **Every database change is a migration.** Migrations have to be reversible, and "add" and "delete" changes go in separate steps. The rules are in [AGENT.md](AGENT.md).

No email is sent yet. When you invite someone, the invite token is shown on screen, and you pass it along yourself.

## Running it

You need [Docker](https://www.docker.com/) installed. That's enough for the quick start.

### Quick start (everything in Docker)

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

Open `backend/.env` and set `SECRET_KEY` to a long random string. This command makes one:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Then start everything:

```bash
docker compose up --build
```

This starts the database, the backend and the frontend. The backend applies database migrations when it starts. Code changes reload automatically.

- App: http://localhost:3000
- API docs (try the endpoints in your browser): http://localhost:8000/docs

### Demo credentials

The fastest way to look around is to load the demo data:

```bash
docker compose exec backend python -m app.cli seed-demo
```

This creates a tenant called `demo` with one published course, "Getting started", already assigned to the learner. Every account uses the password `demo-password-123`:

| Account | Email | Tenant slug at login |
| --- | --- | --- |
| Platform superadmin | `superadmin@demo.example.com` | leave empty |
| Tenant admin | `admin@demo.example.com` | `demo` |
| Learner | `learner@demo.example.com` | `demo` |

Running it again does nothing if the demo tenant already exists. It refuses to run when `ENVIRONMENT=production`, because the password is public.

### Create the first account

Without the demo data, the database starts empty, and there's no sign-up page, so you create the first platform account from the command line:

```bash
docker compose exec backend python -m app.cli create-superadmin you@example.com
```

It asks for a password. Add `--role admin` or `--role superviewer` to create those roles instead.

Then:

1. Log in at http://localhost:3000 with that email and password. Leave the "Tenant slug" field empty.
2. Create a tenant and invite its tenant admin. Copy the invite token it shows.
3. Log out, open http://localhost:3000/accept-invite, paste the token and pick a password.
4. Log in as the tenant admin with the tenant's slug (its short URL name), then invite learners and add courses the same way.

### Running without Docker (except the database)

Useful if you want your editor's debugger. You'll need [uv](https://docs.astral.sh/uv/) and Node.js 24.

```bash
docker compose up -d db                  # just the database

cd backend
uv sync                                  # install Python packages
uv run alembic upgrade head              # create the tables
uv run fastapi dev app/main.py           # http://localhost:8000

cd frontend                              # in a second terminal
npm install
npm run dev                              # http://localhost:3000
```

Create the first account with `uv run python -m app.cli create-superadmin you@example.com` from `backend/`.

### Expiring trials

Run this on a schedule, hourly for example. Running it twice, or twice at once, is safe:

```bash
uv run python -m app.cli expire-trials
```

## Tests and checks

Backend tests run against a real PostgreSQL database, not a fake one, so start it first with `docker compose up -d db`. The tests create their own `learning_platform_test` database and leave your data alone.

```bash
cd backend  && uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest
cd frontend && npm run lint && npm run typecheck && npm run build
```

The tests focus on what would hurt most if it broke: logging in, role permissions, tenant isolation, trial expiry, course assignment and progress.

## Where things are

```
.
├── compose.yml                  # runs db + backend + frontend
├── AGENT.md                     # rules for changes: migrations, tests, change log
├── CHANGES.md                   # what changed and why, newest first
├── docs/tenant-trial.md         # how the free trial works
├── backend/
│   ├── alembic/versions/        # database migrations
│   ├── app/
│   │   ├── api/deps.py          # who's logged in, which tenant, what they may do
│   │   ├── api/v1/endpoints/    # the HTTP routes
│   │   ├── services/            # business rules
│   │   ├── repositories/        # database reads and writes, tenant-filtered
│   │   ├── models/              # database tables
│   │   ├── schemas/             # shapes of request and response data
│   │   ├── core/                # settings, database connection, password hashing
│   │   └── cli.py               # command-line admin commands
│   └── tests/
└── frontend/src/
    ├── app/                     # pages
    ├── features/                # screens per area: auth, platform, tenant, learner
    ├── lib/api/client.ts        # the typed API client
    └── types/api.d.ts           # generated from the backend, don't edit by hand
```

## Adding a new feature

Say you want lessons inside courses:

1. Add a model in `backend/app/models/lesson.py` that includes `TenantScopedMixin`, which gives it the `tenant_id` column. Export it from `app/models/__init__.py`.
2. Generate a migration with `uv run alembic revision --autogenerate -m "add lessons"`, read it over, then run `uv run alembic upgrade head`.
3. Add a schema, a repository based on `TenantScopedRepository`, a service and an endpoint. Register the endpoint in `app/api/v1/router.py`.
4. With the backend running, run `npm run gen:api` in `frontend/` to update the frontend types.
5. Write tests, including one that checks another tenant can't reach the new data, and add an entry to `CHANGES.md`.

## Deploying

Both Dockerfiles have a `prod` target:

```bash
docker build --target prod -t lp-backend ./backend
docker build --target prod --build-arg NEXT_PUBLIC_API_URL=https://api.example.com -t lp-frontend ./frontend
```

Two differences from local development:

- The production backend doesn't run migrations on startup. Run `alembic upgrade head` as its own release step, so several app instances don't race to change the database.
- Outside `ENVIRONMENT=local`, the backend refuses to start unless `SECRET_KEY` is at least 32 random characters. With `ENVIRONMENT=production`, the API docs page is also turned off.
