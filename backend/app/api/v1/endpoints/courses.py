import uuid

from fastapi import APIRouter, status

from app.api.deps import DBSession, LearningManager, LearningMember, Pagination, TenantContext
from app.schemas.common import Page
from app.schemas.course import CourseCreate, CourseRead, CourseUpdate
from app.schemas.enrollment import EnrollmentCreate, EnrollmentRead, ProgressUpdate
from app.services import CourseService, EnrollmentService

router = APIRouter()


def _visible_courses(ctx: TenantContext, db: DBSession) -> CourseService:
    # Tenantadmins see every course; users only published courses assigned to them.
    return CourseService(db, ctx.tenant_id, None if ctx.can_manage else ctx.user.id)


@router.get("", response_model=Page[CourseRead])
async def list_courses(ctx: LearningMember, db: DBSession, page: Pagination) -> Page[CourseRead]:
    items, total = await _visible_courses(ctx, db).list(limit=page.limit, offset=page.offset)
    return Page(
        items=[CourseRead.model_validate(c) for c in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post("", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
async def create_course(data: CourseCreate, ctx: LearningManager, db: DBSession) -> CourseRead:
    course = await CourseService(db, ctx.tenant_id).create(data, created_by_id=ctx.user.id)
    return CourseRead.model_validate(course)


@router.get("/{course_id}", response_model=CourseRead)
async def get_course(course_id: uuid.UUID, ctx: LearningMember, db: DBSession) -> CourseRead:
    course = await _visible_courses(ctx, db).get(course_id)
    return CourseRead.model_validate(course)


@router.patch("/{course_id}", response_model=CourseRead)
async def update_course(
    course_id: uuid.UUID, data: CourseUpdate, ctx: LearningManager, db: DBSession
) -> CourseRead:
    course = await CourseService(db, ctx.tenant_id).update(course_id, data)
    return CourseRead.model_validate(course)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(course_id: uuid.UUID, ctx: LearningManager, db: DBSession) -> None:
    await CourseService(db, ctx.tenant_id).delete(course_id)


@router.post(
    "/{course_id}/enrollments", response_model=EnrollmentRead, status_code=status.HTTP_201_CREATED
)
async def assign_course(
    course_id: uuid.UUID, data: EnrollmentCreate, ctx: LearningManager, db: DBSession
) -> EnrollmentRead:
    enrollment = await EnrollmentService(db, ctx.tenant_id).assign(course_id, data.user_id)
    return EnrollmentRead.model_validate(enrollment)


@router.get("/{course_id}/enrollments", response_model=Page[EnrollmentRead])
async def list_course_enrollments(
    course_id: uuid.UUID, ctx: LearningManager, db: DBSession, page: Pagination
) -> Page[EnrollmentRead]:
    """Who the course is assigned to, with each user's progress."""
    items, total = await EnrollmentService(db, ctx.tenant_id).list_for_course(
        course_id, limit=page.limit, offset=page.offset
    )
    return Page(
        items=[EnrollmentRead.model_validate(e) for e in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.delete("/{course_id}/enrollments/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unassign_course(
    course_id: uuid.UUID, user_id: uuid.UUID, ctx: LearningManager, db: DBSession
) -> None:
    await EnrollmentService(db, ctx.tenant_id).unassign(course_id, user_id)


@router.get("/{course_id}/progress", response_model=EnrollmentRead)
async def get_my_progress(
    course_id: uuid.UUID, ctx: LearningMember, db: DBSession
) -> EnrollmentRead:
    enrollment = await EnrollmentService(db, ctx.tenant_id).get_own(course_id, ctx.user.id)
    return EnrollmentRead.model_validate(enrollment)


@router.put("/{course_id}/progress", response_model=EnrollmentRead)
async def set_my_progress(
    course_id: uuid.UUID, data: ProgressUpdate, ctx: LearningMember, db: DBSession
) -> EnrollmentRead:
    enrollment = await EnrollmentService(db, ctx.tenant_id).set_progress(
        course_id, ctx.user.id, data.progress_percent
    )
    return EnrollmentRead.model_validate(enrollment)
