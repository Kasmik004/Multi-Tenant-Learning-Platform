import enum
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TenantStatus(enum.StrEnum):
    """Lifecycle: created -> trial_active -> expired (-> trial_active again when extended).

    "Created" is not stored: a tenant's trial starts in the same transaction that creates it.
    """

    TRIAL_ACTIVE = "trial_active"
    EXPIRED = "expired"


class Tenant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(200))
    # URL-safe identifier; usable for subdomains (acme.example.com) or login lookup.
    slug: Mapped[str] = mapped_column(String(63), unique=True, index=True)
    # Manual suspension by the platform; locks members out entirely, unlike trial expiry.
    is_active: Mapped[bool] = mapped_column(default=True)
    # Recorded status, written by the expiry sweep and by trial extensions. Access checks use
    # `trial_expired`, which also honors trial_ends_at, so they never wait for the sweep.
    status: Mapped[TenantStatus] = mapped_column(
        Enum(TenantStatus, name="tenant_status", values_callable=lambda e: [m.value for m in e]),
        default=TenantStatus.TRIAL_ACTIVE,
        server_default=TenantStatus.TRIAL_ACTIVE.value,
    )
    trial_ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # When the sweep recorded the expiry; cleared when the trial is extended.
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def trial_expired(self) -> bool:
        return self.status == TenantStatus.EXPIRED or self.trial_ends_at <= datetime.now(UTC)

    @property
    def current_status(self) -> TenantStatus:
        return TenantStatus.EXPIRED if self.trial_expired else TenantStatus.TRIAL_ACTIVE
