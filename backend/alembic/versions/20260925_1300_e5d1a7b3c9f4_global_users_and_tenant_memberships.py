"""global users and tenant memberships

Revision ID: e5d1a7b3c9f4
Revises: c4a8f2e61b90
Create Date: 2026-09-25 13:00:00.000000

"""

# Why: a user can belong to several tenants, so tenant access moves from users.tenant_id/role
# to tenant_memberships; old columns are only deprecated here and dropped in a later migration.

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "e5d1a7b3c9f4"
down_revision: str | None = "c4a8f2e61b90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

platform_role = postgresql.ENUM("superadmin", "admin", "superviewer", name="platform_role")
tenant_role = postgresql.ENUM("tenantadmin", "user", name="tenant_role")
membership_status = postgresql.ENUM("pending", "active", "rejected", name="membership_status")


def upgrade() -> None:
    bind = op.get_bind()
    for enum in (platform_role, tenant_role, membership_status):
        enum.create(bind, checkfirst=True)

    op.add_column(
        "users",
        sa.Column("platform_role", postgresql.ENUM(name="platform_role", create_type=False)),
    )
    op.add_column("users", sa.Column("merged_into_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_users_merged_into_id_users"),
        "users",
        "users",
        ["merged_into_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "tenant_memberships",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", postgresql.ENUM(name="tenant_role", create_type=False), nullable=False),
        sa.Column(
            "status", postgresql.ENUM(name="membership_status", create_type=False), nullable=False
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_tenant_memberships_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_tenant_memberships_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tenant_memberships")),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_tenant_memberships_tenant_id_user_id"),
    )
    op.create_index(op.f("ix_tenant_memberships_tenant_id"), "tenant_memberships", ["tenant_id"])
    op.create_index(op.f("ix_tenant_memberships_user_id"), "tenant_memberships", ["user_id"])

    # Merge: the oldest account per email becomes the global user; the rest point at it.
    op.execute(
        """
        UPDATE users u SET merged_into_id = c.id
        FROM (
            SELECT DISTINCT ON (email) email, id FROM users ORDER BY email, created_at, id
        ) c
        WHERE u.email = c.email AND u.id <> c.id
        """
    )
    # Every old per-tenant account becomes an active membership of its global user.
    # Old 'admin' was the tenant's administrator (created at onboarding) -> tenantadmin.
    op.execute(
        """
        INSERT INTO tenant_memberships (id, tenant_id, user_id, role, status, created_at)
        SELECT gen_random_uuid(), u.tenant_id, COALESCE(u.merged_into_id, u.id),
               CASE WHEN u.role::text IN ('admin', 'tenantadmin') THEN 'tenantadmin'
                    ELSE 'user' END::tenant_role,
               'active'::membership_status, u.created_at
        FROM users u
        WHERE u.role::text NOT IN ('superadmin', 'superviewer')
        """
    )
    # Platform-level roles move onto the global user; superadmin wins over superviewer.
    op.execute(
        """
        UPDATE users c SET platform_role = x.platform_role
        FROM (
            SELECT COALESCE(merged_into_id, id) AS user_id,
                   CASE WHEN bool_or(role::text = 'superadmin') THEN 'superadmin'
                        ELSE 'superviewer' END::platform_role AS platform_role
            FROM users
            WHERE role::text IN ('superadmin', 'superviewer')
            GROUP BY 1
        ) x
        WHERE c.id = x.user_id
        """
    )

    # Deprecated: new global users have no single tenant or tenant role.
    op.alter_column("users", "tenant_id", existing_type=sa.Uuid(), nullable=True)
    op.alter_column("users", "role", existing_type=postgresql.ENUM(name="user_role"), nullable=True)
    op.create_index(
        "uq_users_email_active",
        "users",
        ["email"],
        unique=True,
        postgresql_where=sa.text("merged_into_id IS NULL"),
    )


def downgrade() -> None:
    # Users created after the upgrade get tenant_id/role back from their oldest active
    # membership (a pending join request must not turn into access).
    # A user can only map back to one tenant, so extra memberships and join requests are lost.
    op.execute(
        """
        UPDATE users u SET tenant_id = m.tenant_id,
               role = CASE
                   WHEN u.platform_role IS NOT NULL THEN u.platform_role::text
                   WHEN m.role = 'tenantadmin' THEN 'admin'
                   ELSE 'user' END::user_role
        FROM (
            SELECT DISTINCT ON (user_id) user_id, tenant_id, role
            FROM tenant_memberships WHERE status = 'active'
            ORDER BY user_id, created_at, id
        ) m
        WHERE u.tenant_id IS NULL AND m.user_id = u.id
        """
    )
    orphans = op.get_bind().scalar(
        sa.text("SELECT count(*) FROM users WHERE tenant_id IS NULL OR role IS NULL")
    )
    if orphans:
        raise RuntimeError(
            f"{orphans} user(s) belong to no tenant and can't exist in the old schema; "
            "add them to a tenant or delete them before downgrading."
        )

    op.drop_index("uq_users_email_active", table_name="users")
    op.alter_column(
        "users", "role", existing_type=postgresql.ENUM(name="user_role"), nullable=False
    )
    op.alter_column("users", "tenant_id", existing_type=sa.Uuid(), nullable=False)

    op.drop_index(op.f("ix_tenant_memberships_user_id"), table_name="tenant_memberships")
    op.drop_index(op.f("ix_tenant_memberships_tenant_id"), table_name="tenant_memberships")
    op.drop_table("tenant_memberships")
    op.drop_constraint(op.f("fk_users_merged_into_id_users"), "users", type_="foreignkey")
    op.drop_column("users", "merged_into_id")
    op.drop_column("users", "platform_role")

    bind = op.get_bind()
    for enum in (membership_status, tenant_role, platform_role):
        enum.drop(bind, checkfirst=True)
