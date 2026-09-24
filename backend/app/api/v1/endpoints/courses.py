import uuid

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DBSession, Pagination, StaffUser
from app.schemas.common import Page
from app.schemas.course import CourseCreate, CourseRead, CourseUpdate
from app.services import CourseService

router = APIRouter()


@router.get("", response_model=Page[CourseRead])
async def list_courses(user: CurrentUser, db: DBSession, page: Pagination) -> Page[CourseRead]:
    items, total = await CourseService(db, user.tenant_id).list(
        limit=page.limit, offset=page.offset
    )
    return Page(
        items=[CourseRead.model_validate(c) for c in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post("", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
async def create_course(data: CourseCreate, user: StaffUser, db: DBSession) -> CourseRead:
    course = await CourseService(db, user.tenant_id).create(data, created_by_id=user.id)
    return CourseRead.model_validate(course)


@router.get("/{course_id}", response_model=CourseRead)
async def get_course(course_id: uuid.UUID, user: CurrentUser, db: DBSession) -> CourseRead:
    course = await CourseService(db, user.tenant_id).get(course_id)
    return CourseRead.model_validate(course)


@router.patch("/{course_id}", response_model=CourseRead)
async def update_course(
    course_id: uuid.UUID, data: CourseUpdate, user: StaffUser, db: DBSession
) -> CourseRead:
    course = await CourseService(db, user.tenant_id).update(course_id, data)
    return CourseRead.model_validate(course)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(course_id: uuid.UUID, user: StaffUser, db: DBSession) -> None:
    await CourseService(db, user.tenant_id).delete(course_id)
