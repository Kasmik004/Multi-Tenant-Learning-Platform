import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.course import Course
from app.repositories import CourseRepository
from app.schemas.course import CourseCreate, CourseUpdate


class CourseService:
    def __init__(
        self, session: AsyncSession, tenant_id: uuid.UUID, learner_id: uuid.UUID | None = None
    ) -> None:
        """learner_id: restrict to that user's assigned, published courses."""
        self.session = session
        self.courses = CourseRepository(session, tenant_id, learner_id)

    async def list(self, *, limit: int, offset: int) -> tuple[list[Course], int]:
        return await self.courses.list(limit=limit, offset=offset)

    async def get(self, course_id: uuid.UUID) -> Course:
        course = await self.courses.get(course_id)
        if course is None:
            raise NotFoundError("Course not found")
        return course

    async def create(self, data: CourseCreate, *, created_by_id: uuid.UUID) -> Course:
        course = await self.courses.add(Course(**data.model_dump(), created_by_id=created_by_id))
        await self.session.commit()
        return course

    async def update(self, course_id: uuid.UUID, data: CourseUpdate) -> Course:
        course = await self.get(course_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(course, field, value)
        await self.session.commit()
        await self.session.refresh(course)
        return course

    async def delete(self, course_id: uuid.UUID) -> None:
        await self.courses.delete(await self.get(course_id))
        await self.session.commit()
