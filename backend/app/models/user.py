import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PlatformRole(enum.StrEnum):
    SUPERADMIN = "superadmin"  # creates and manages tenants
    ADMIN = "admin"  # superadmin minus creating/deleting tenants
    SUPERVIEWER = "superviewer"  # read-only everywhere


class TenantRole(enum.StrEnum):
    TENANTADMIN = "tenantadmin"  # manages users and courses in the tenant
    USER = "user"  # learner


def _enum(cls: type[enum.StrEnum], name: str) -> Enum:
    return Enum(cls, name=name, values_callable=lambda e: [m.value for m in e])


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An account in exactly one tenant, or a platform account (tenant_id is NULL).

    The same email may hold separate accounts in different tenants.
    """

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_id_email"),
        Index(
            "uq_users_email_platform",
            "email",
            unique=True,
            postgresql_where=text("tenant_id IS NULL"),
        ),
    )

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(String(320))
    # NULL until the invite is accepted; such accounts can't log in.
    hashed_password: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(200))
    tenant_role: Mapped[TenantRole | None] = mapped_column(_enum(TenantRole, "tenant_role"))
    platform_role: Mapped[PlatformRole | None] = mapped_column(_enum(PlatformRole, "platform_role"))
    is_active: Mapped[bool] = mapped_column(default=True)
    # sha256 of the single-use invite token; cleared once accepted.
    invite_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    invite_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def invite_pending(self) -> bool:
        return self.hashed_password is None
