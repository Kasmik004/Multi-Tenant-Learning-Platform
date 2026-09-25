"""tenant trial lifecycle

Revision ID: b7d2e4f6a1c3
Revises: a9c3e7f1d2b8
Create Date: 2026-09-26 14:00:00.000000

"""

# Why: new tenants get a free trial (trial_active -> expired) after which learning is blocked;
# existing tenants get a full trial from the moment this ships so nobody is cut off on deploy.

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "b7d2e4f6a1c3"
down_revision: str | None = "a9c3e7f1d2b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Mirrors the default settings.TRIAL_DAYS; frozen here so the migration never changes meaning.
_BACKFILL_TRIAL_DAYS = 14


def upgrade() -> None:
    postgresql.ENUM("trial_active", "expired", name="tenant_status").create(
        op.get_bind(), checkfirst=True
    )
    op.add_column(
        "tenants",
        sa.Column(
            "status",
            postgresql.ENUM(name="tenant_status", create_type=False),
            nullable=False,
            server_default="trial_active",
        ),
    )
    op.add_column("tenants", sa.Column("trial_ends_at", sa.DateTime(timezone=True)))
    op.add_column("tenants", sa.Column("expired_at", sa.DateTime(timezone=True)))
    op.execute(f"UPDATE tenants SET trial_ends_at = now() + interval '{_BACKFILL_TRIAL_DAYS} days'")
    op.alter_column(
        "tenants", "trial_ends_at", existing_type=sa.DateTime(timezone=True), nullable=False
    )


def downgrade() -> None:
    # Trial dates have no place in the old schema; downgrading simply lifts trial restrictions.
    op.drop_column("tenants", "expired_at")
    op.drop_column("tenants", "trial_ends_at")
    op.drop_column("tenants", "status")
    postgresql.ENUM(name="tenant_status").drop(op.get_bind(), checkfirst=True)
