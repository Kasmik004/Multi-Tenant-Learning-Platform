import enum

from sqlalchemy import Enum, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(enum.StrEnum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    SUPERVIEWER = "superviewer"
    TENANTADMIN = "tenantadmin"
    USER = "user"
    


class User(UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, Base):
    __tablename__ = "users"
    # The same email may exist in different tenants as separate accounts.
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_users_tenant_id_email"),)

    email: Mapped[str] = mapped_column(String(320))
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(200))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda e: [m.value for m in e]),
        default=UserRole.USER,
    )
    is_active: Mapped[bool] = mapped_column(default=True)
