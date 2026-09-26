---
name: backend-migrations
description: How to write, verify and apply Alembic migrations for backend/ under this repo's AGENT.md rules (reversible, additive before destructive, a "why" comment, sign-off for irreversible drops), plus the current revision chain and deprecated columns awaiting removal. Load before changing any model in backend/app/models, writing a migration, running alembic, or debugging DB enum/column errors.
---

# Backend migrations

AGENT.md rules, applied here:

- Every schema change is a migration in `backend/alembic/versions/`. Never ALTER the DB by hand.
- Both `upgrade()` and `downgrade()`. If a downgrade can't restore data, make it **refuse loudly**
  (`raise RuntimeError(...)` after a count query) rather than silently lose or invent data.
- Additive and destructive steps go in **separate** migrations: deprecate/backfill first (make old
  columns nullable, stop mapping them in the model), drop later.
- Genuinely irreversible drops need explicit user sign-off before writing or running them.
- One-line `# Why:` comment under the docstring (keep lines ≤ 100 chars, ruff enforces it).

## Writing one

File name: `YYYYMMDD_HHMM_<rev>_<slug>.py` (see `alembic.ini`). Set `down_revision` to the current
head (`uv run alembic heads`). Autogenerate is a starting point only: `uv run alembic revision
--autogenerate -m "..."`, then review. It misses enum value changes and data backfills.

Postgres specifics:

- New enum values: `op.execute("ALTER TYPE t ADD VALUE IF NOT EXISTS 'v'")`. Removing values needs
  the type rebuilt (rename old → create new → `ALTER COLUMN ... USING col::text::new` → drop old).
- Create an enum type once with `postgresql.ENUM(..., name=...).create(bind, checkfirst=True)`, and
  reference it in columns with `postgresql.ENUM(name=..., create_type=False)`.
- Partial unique indexes: `op.create_index(..., unique=True, postgresql_where=sa.text("..."))`.
  Mirror them in the model's `__table_args__` so tests (which use `create_all`) get them too.
- Backfills are plain SQL in `op.execute`. `DISTINCT ON (...) ORDER BY ...` picks "oldest per group".

## Verify before reporting done

Never test against the dev DB (`learning_platform`). Use the bundled script, which works on a
throwaway `migration_check` database. Run from `backend/`:

```bash
uv run python ../.claude/skills/backend-migrations/check_migrations.py
```

It checks: upgrade base→head, downgrade head→base, upgrade again, then compares the migrated
schema to the models (only known deprecated leftovers should differ). For data backfills, also
test with representative rows: run with `--keep` (leaves `migration_check` at head), then with
`POSTGRES_DB=migration_check` downgrade to the previous revision, seed rows (for example the same
email in two tenants, a platform user, a pending invite), upgrade, inspect, downgrade again, and
drop the DB when done.

Then the normal gates: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`,
`uv run mypy app`.

## Applying

The dev DB is the user's; don't upgrade it unless they ask. Tell them to run
`uv run alembic upgrade head` from `backend/`.

## Revision chain (head last)

1. `2ccde2d17141`: initial schema (tenants, users, courses)
2. `7b3e9c1a4d2f`: add superadmin/superviewer/tenantadmin/user to `user_role` enum
3. `c4a8f2e61b90`: `users.full_name` nullable
4. `e5d1a7b3c9f4`: global users + `tenant_memberships`, merge duplicate emails (superseded)
5. `a9c3e7f1d2b8`: per-tenant users again: `tenant_role`, invite columns, un-merge.
6. `b7d2e4f6a1c3`: tenant trial (`status` enum `tenant_status`, `trial_ends_at`, `expired_at`);
   existing tenants backfilled with a 14-day trial.
7. `d4f8a2c6e9b1`: drops the deprecated `tenant_memberships`, `users.role`, `users.merged_into_id`,
   `user_role` and `membership_status` (destructive; downgrade restores empty structure).
8. `f1a3c5e7b9d2`: `enrollments` (course assignment + progress, `progress_status` enum). **Head.**

The drift check should report `(none)`; anything it lists is a real mismatch.
