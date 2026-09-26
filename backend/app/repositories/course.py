import uuid

from sqlalchemy import Select, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course
from app.models.enrollment import Enrollment
from app.repositories.base import TenantScopedRepository


class CourseRepository(TenantScopedRepository[Course]):
    """With `learner_id`, only published courses assigned to that user are visible."""

    model = Course

    def __init__(
        self, session: AsyncSession, tenant_id: uuid.UUID, learner_id: uuid.UUID | None = None
    ) -> None:
        super().__init__(session, tenant_id)
        self.learner_id = learner_id

    def _query(self) -> Select[tuple[Course]]:
        query = super()._query().order_by(Course.created_at.desc())
        if self.learner_id is not None:
            assigned = exists().where(
                Enrollment.course_id == Course.id, Enrollment.user_id == self.learner_id
            )
            query = query.where(Course.is_published, assigned)
        return query

    def ids(self) -> Select[tuple[uuid.UUID]]:
        """Ids of the visible courses, for use as a subquery."""
        return select(self._query().subquery().c.id)
