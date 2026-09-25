"""make user full_name nullable

Revision ID: c4a8f2e61b90
Revises: 7b3e9c1a4d2f
Create Date: 2026-09-25 12:10:00.000000

"""

# Why: self-registration doesn't collect a full name, so users can now exist without one.

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c4a8f2e61b90"
down_revision: str | None = "7b3e9c1a4d2f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("users", "full_name", existing_type=sa.String(length=200), nullable=True)


def downgrade() -> None:
    # Backfill NULLs with an empty string so NOT NULL can be restored.
    op.execute("UPDATE users SET full_name = '' WHERE full_name IS NULL")
    op.alter_column("users", "full_name", existing_type=sa.String(length=200), nullable=False)
