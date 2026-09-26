"""drop deprecated membership columns

Revision ID: d4f8a2c6e9b1
Revises: b7d2e4f6a1c3
Create Date: 2026-09-26 15:00:00.000000

"""

# Why: tenant_memberships, users.role and users.merged_into_id were superseded by per-tenant
# accounts in a9c3e7f1d2b8 and no code reads them; dropped with user sign-off (2026-09-26).

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "d4f8a2c6e9b1"
down_revision: str | None = "b7d2e4f6a1c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Values the deprecated enums held at the time they were dropped.
_USER_ROLE = ("admin", "instructor", "learner", "superadmin", "superviewer", "tenantadmin", "user")
_MEMBERSHIP_STATUS = ("pending", "active", "rejected")


def upgrade() -> None:
    op.drop_index(op.f("ix_tenant_memberships_user_id"), table_name="tenant_memberships")
    op.drop_index(op.f("ix_tenant_memberships_tenant_id"), table_name="tenant_memberships")
    op.drop_table("tenant_memberships")
    op.drop_constraint(op.f("fk_users_merged_into_id_users"), "users", type_="foreignkey")
    op.drop_column("users", "merged_into_id")
    op.drop_column("users", "role")
    bind = op.get_bind()
    postgresql.ENUM(name="membership_status").drop(bind, checkfirst=True)
    postgresql.ENUM(name="user_role").drop(bind, checkfirst=True)


def downgrade() -> None:
    # Restores the structure only (empty); the a9c3e7f1d2b8 downgrade refills it from
    # users.tenant_role if you keep going down. The dropped rows themselves are not recoverable.
    bind = op.get_bind()
    postgresql.ENUM(*_USER_ROLE, name="user_role").create(bind, checkfirst=True)
    postgresql.ENUM(*_MEMBERSHIP_STATUS, name="membership_status").create(bind, checkfirst=True)
    op.add_column("users", sa.Column("role", postgresql.ENUM(name="user_role", create_type=False)))
    op.add_column("users", sa.Column("merged_into_id", sa.Uuid()))
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
