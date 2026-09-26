# Import every model here so Base.metadata is complete for Alembic autogenerate.
from app.models.base import Base
from app.models.course import Course
from app.models.enrollment import Enrollment, ProgressStatus
from app.models.tenant import Tenant, TenantStatus
from app.models.user import PlatformRole, TenantRole, User

__all__ = [
    "Base",
    "Course",
    "Enrollment",
    "PlatformRole",
    "ProgressStatus",
    "Tenant",
    "TenantRole",
    "TenantStatus",
    "User",
]
