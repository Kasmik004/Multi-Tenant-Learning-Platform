"""per-tenant users with invites

Revision ID: a9c3e7f1d2b8
Revises: e5d1a7b3c9f4
Create Date: 2026-09-26 10:00:00.000000

"""

# Why: each tenant is a separate organization, so an account belongs to exactly one tenant
# and joins by admin invite; tenant_memberships/users.role/merged_into_id are only deprecated.

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a9c3e7f1d2b8"
down_revision: str | None = "e5d1a7b3c9f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("tenant_role", postgresql.ENUM(name="tenant_role", create_type=False)),
    )
    op.add_column("users", sa.Column("invite_token_hash", sa.String(length=64)))
    op.add_column("users", sa.Column("invite_expires_at", sa.DateTime(timezone=True)))
    op.create_unique_constraint(op.f("uq_users_invite_token_hash"), "users", ["invite_token_hash"])
    op.alter_column("users", "hashed_password", existing_type=sa.String(255), nullable=True)

    # Accounts created by the multi-tenant code have no tenant_id; use their oldest active
    # membership (a user can now belong to only one tenant).
    op.execute(
        """
        UPDATE users u SET tenant_id = m.tenant_id
        FROM (
            SELECT DISTINCT ON (user_id) user_id, tenant_id FROM tenant_memberships
            WHERE status = 'active' ORDER BY user_id, created_at, id
        ) m
        WHERE u.tenant_id IS NULL AND u.platform_role IS NULL AND m.user_id = u.id
        """
    )
    # Tenant role comes from the active membership for the account's own tenant; merged
    # duplicates' memberships live on the account they were merged into.
    op.execute(
        """
        UPDATE users u SET tenant_role = m.role
        FROM tenant_memberships m
        WHERE u.platform_role IS NULL AND m.status = 'active'
          AND m.tenant_id = u.tenant_id AND m.user_id = COALESCE(u.merged_into_id, u.id)
        """
    )
    # Undo the email merge: per-tenant accounts are separate again (own password kept).
    op.drop_index("uq_users_email_active", table_name="users")
    op.execute("UPDATE users SET merged_into_id = NULL")
    op.create_index(
        "uq_users_email_platform",
        "users",
        ["email"],
        unique=True,
        postgresql_where=sa.text("tenant_id IS NULL"),
    )


def downgrade() -> None:
    pending = op.get_bind().scalar(
        sa.text("SELECT count(*) FROM users WHERE hashed_password IS NULL")
    )
    if pending:
        raise RuntimeError(
            f"{pending} invite(s) not yet accepted can't exist in the old schema; "
            "delete them or have them accepted before downgrading."
        )

    op.drop_index("uq_users_email_platform", table_name="users")
    # Invited accounts never had the deprecated role; fill it so older downgrades still work.
    op.execute(
        """
        UPDATE users SET role = CASE
            WHEN platform_role IS NOT NULL THEN platform_role::text
            WHEN tenant_role = 'tenantadmin' THEN 'admin'
            ELSE 'user' END::user_role
        WHERE role IS NULL AND (tenant_role IS NOT NULL OR platform_role IS NOT NULL)
        """
    )
    # Re-merge by email and give every tenant account an active membership again.
    op.execute(
        """
        UPDATE users u SET merged_into_id = c.id
        FROM (
            SELECT DISTINCT ON (email) email, id FROM users ORDER BY email, created_at, id
        ) c
        WHERE u.email = c.email AND u.id <> c.id
        """
    )
    op.execute(
        """
        INSERT INTO tenant_memberships (id, tenant_id, user_id, role, status, created_at)
        SELECT gen_random_uuid(), u.tenant_id, COALESCE(u.merged_into_id, u.id), u.tenant_role,
               'active', u.created_at
        FROM users u
        WHERE u.tenant_id IS NOT NULL AND u.tenant_role IS NOT NULL
        ON CONFLICT (tenant_id, user_id)
        DO UPDATE SET role = EXCLUDED.role, status = 'active'
        """
    )
    op.create_index(
        "uq_users_email_active",
        "users",
        ["email"],
        unique=True,
        postgresql_where=sa.text("merged_into_id IS NULL"),
    )

    op.alter_column("users", "hashed_password", existing_type=sa.String(255), nullable=False)
    op.drop_constraint(op.f("uq_users_invite_token_hash"), "users", type_="unique")
    op.drop_column("users", "invite_expires_at")
    op.drop_column("users", "invite_token_hash")
    op.drop_column("users", "tenant_role")
