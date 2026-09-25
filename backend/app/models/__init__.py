# Import every model here so Base.metadata is complete for Alembic autogenerate.
from app.models.base import Base
from app.models.course import Course
from app.models.tenant import Tenant
from app.models.user import PlatformRole, TenantRole, User

__all__ = ["Base", "Course", "PlatformRole", "Tenant", "TenantRole", "User"]
