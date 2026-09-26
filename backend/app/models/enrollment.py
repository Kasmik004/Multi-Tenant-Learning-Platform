import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ProgressStatus(enum.StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Enrollment(UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, Base):
    """A course assigned to a user by a tenantadmin, with the user's progress on it."""

    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("course_id", "user_id", name="uq_enrollments_course_id_user_id"),
        CheckConstraint("progress_percent BETWEEN 0 AND 100", name="progress_percent_range"),
    )

    course_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Derived from progress_percent by the service (0 / 1-99 / 100); stored for filtering.
    status: Mapped[ProgressStatus] = mapped_column(
        Enum(
            ProgressStatus, name="progress_status", values_callable=lambda e: [m.value for m in e]
        ),
        default=ProgressStatus.NOT_STARTED,
    )
    progress_percent: Mapped[int] = mapped_column(default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
