from sqlalchemy import Select

from app.models.course import Course
from app.repositories.base import TenantScopedRepository


class CourseRepository(TenantScopedRepository[Course]):
    model = Course

    def _query(self) -> Select[tuple[Course]]:
        return super()._query().order_by(Course.created_at.desc())
