import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.enrollment import Enrollment, ProgressStatus
from app.repositories import CourseRepository, EnrollmentRepository, TenantUserRepository


class EnrollmentService:
    """Course assignment (by tenantadmins) and learners' progress, within one tenant."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.enrollments = EnrollmentRepository(session, tenant_id)

    async def _require_course(self, course_id: uuid.UUID) -> None:
        if await CourseRepository(self.session, self.tenant_id).get(course_id) is None:
            raise NotFoundError("Course not found")

    async def assign(self, course_id: uuid.UUID, user_id: uuid.UUID) -> Enrollment:
        await self._require_course(course_id)
        if await TenantUserRepository(self.session, self.tenant_id).get(user_id) is None:
            raise NotFoundError("User not found")
        if await self.enrollments.get_for(course_id, user_id):
            raise ConflictError("The course is already assigned to this user")
        try:
            enrollment = await self.enrollments.add(
                Enrollment(course_id=course_id, user_id=user_id)
            )
            await self.session.commit()
        except IntegrityError as exc:  # lost a race on the unique (course, user)
            await self.session.rollback()
            raise ConflictError("The course is already assigned to this user") from exc
        await self.session.refresh(enrollment)
        return enrollment

    async def list_for_course(
        self, course_id: uuid.UUID, *, limit: int, offset: int
    ) -> tuple[list[Enrollment], int]:
        await self._require_course(course_id)
        return await self.enrollments.list_for_course(course_id, limit=limit, offset=offset)

    async def unassign(self, course_id: uuid.UUID, user_id: uuid.UUID) -> None:
        enrollment = await self.enrollments.get_for(course_id, user_id)
        if enrollment is None:
            raise NotFoundError("Enrollment not found")
        await self.enrollments.delete(enrollment)
        await self.session.commit()

    async def list_own(
        self, user_id: uuid.UUID, *, limit: int, offset: int
    ) -> tuple[list[Enrollment], int]:
        visible = CourseRepository(self.session, self.tenant_id, learner_id=user_id)
        return await self.enrollments.list_where(
            Enrollment.user_id == user_id,
            Enrollment.course_id.in_(visible.ids()),
            limit=limit,
            offset=offset,
        )

    async def get_own(self, course_id: uuid.UUID, user_id: uuid.UUID) -> Enrollment:
        # Only courses the learner can see (assigned and published) carry progress.
        visible = CourseRepository(self.session, self.tenant_id, learner_id=user_id)
        enrollment = await self.enrollments.get_for(course_id, user_id)
        if enrollment is None or await visible.get(course_id) is None:
            raise NotFoundError("Course not found")
        return enrollment

    async def set_progress(
        self, course_id: uuid.UUID, user_id: uuid.UUID, percent: int
    ) -> Enrollment:
        enrollment = await self.get_own(course_id, user_id)
        enrollment.progress_percent = percent
        if percent == 100:
            enrollment.status = ProgressStatus.COMPLETED
            enrollment.completed_at = enrollment.completed_at or datetime.now(UTC)
        else:
            enrollment.status = (
                ProgressStatus.IN_PROGRESS if percent > 0 else ProgressStatus.NOT_STARTED
            )
            enrollment.completed_at = None
        await self.session.commit()
        await self.session.refresh(enrollment)
        return enrollment
