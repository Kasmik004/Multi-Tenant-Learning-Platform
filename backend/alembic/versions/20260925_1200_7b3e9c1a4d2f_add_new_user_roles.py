"""add new user roles

Revision ID: 7b3e9c1a4d2f
Revises: 2ccde2d17141
Create Date: 2026-09-25 12:00:00.000000

"""

# Why: UserRole gained superadmin/superviewer/tenantadmin/user, so the DB type must accept them.

from collections.abc import Sequence

from alembic import op

revision: str = "7b3e9c1a4d2f"
down_revision: str | None = "2ccde2d17141"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_VALUES = ("admin", "instructor", "learner")
NEW_VALUES = ("superadmin", "superviewer", "tenantadmin", "user")


def upgrade() -> None:
    for value in NEW_VALUES:
        op.execute(f"ALTER TYPE user_role ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # Postgres can't drop enum values, so rebuild the type. Fails if any row still uses a new value.
    op.execute("ALTER TYPE user_role RENAME TO user_role_new")
    values = ", ".join(f"'{v}'" for v in OLD_VALUES)
    op.execute(f"CREATE TYPE user_role AS ENUM ({values})")
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE user_role USING role::text::user_role")
    op.execute("DROP TYPE user_role_new")
