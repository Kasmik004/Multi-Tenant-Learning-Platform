"""course enrollments and progress

Revision ID: f1a3c5e7b9d2
Revises: d4f8a2c6e9b1
Create Date: 2026-09-26 16:00:00.000000

"""

# Why: tenantadmins assign courses to users and users track progress; until now every user
# saw every course. Existing tenants start with no assignments (users see no courses).

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "f1a3c5e7b9d2"
down_revision: str | None = "d4f8a2c6e9b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    postgresql.ENUM("not_started", "in_progress", "completed", name="progress_status").create(
        op.get_bind(), checkfirst=True
    )
    op.create_table(
        "enrollments",
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status", postgresql.ENUM(name="progress_status", create_type=False), nullable=False
        ),
        sa.Column("progress_percent", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
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
        sa.CheckConstraint(
            "progress_percent BETWEEN 0 AND 100",
            name=op.f("ck_enrollments_progress_percent_range"),
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name=op.f("fk_enrollments_course_id_courses"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_enrollments_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_enrollments_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_enrollments")),
        sa.UniqueConstraint("course_id", "user_id", name="uq_enrollments_course_id_user_id"),
    )
    op.create_index(op.f("ix_enrollments_course_id"), "enrollments", ["course_id"])
    op.create_index(op.f("ix_enrollments_tenant_id"), "enrollments", ["tenant_id"])
    op.create_index(op.f("ix_enrollments_user_id"), "enrollments", ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_enrollments_user_id"), table_name="enrollments")
    op.drop_index(op.f("ix_enrollments_tenant_id"), table_name="enrollments")
    op.drop_index(op.f("ix_enrollments_course_id"), table_name="enrollments")
    op.drop_table("enrollments")
    postgresql.ENUM(name="progress_status").drop(op.get_bind(), checkfirst=True)
