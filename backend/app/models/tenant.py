from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Tenant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(200))
    # URL-safe identifier; usable for subdomains (acme.example.com) or login lookup.
    slug: Mapped[str] = mapped_column(String(63), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)
