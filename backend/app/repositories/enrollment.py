import uuid

from sqlalchemy import Select

from app.models.enrollment import Enrollment
from app.repositories.base import TenantScopedRepository


class EnrollmentRepository(TenantScopedRepository[Enrollment]):
    model = Enrollment

    def _query(self) -> Select[tuple[Enrollment]]:
        return super()._query().order_by(Enrollment.created_at)

    async def get_for(self, course_id: uuid.UUID, user_id: uuid.UUID) -> Enrollment | None:
        result = await self.session.execute(
            self._query().where(Enrollment.course_id == course_id, Enrollment.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_for_course(
        self, course_id: uuid.UUID, *, limit: int, offset: int
    ) -> tuple[list[Enrollment], int]:
        return await self.list_where(Enrollment.course_id == course_id, limit=limit, offset=offset)
