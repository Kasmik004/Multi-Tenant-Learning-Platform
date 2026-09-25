import uuid

from fastapi import APIRouter, status

from app.api.deps import DBSession, Pagination, TenantManager, TenantMember
from app.schemas.common import Page
from app.schemas.course import CourseCreate, CourseRead, CourseUpdate
from app.services import CourseService

router = APIRouter()


@router.get("", response_model=Page[CourseRead])
async def list_courses(ctx: TenantMember, db: DBSession, page: Pagination) -> Page[CourseRead]:
    items, total = await CourseService(db, ctx.tenant_id).list(limit=page.limit, offset=page.offset)
    return Page(
        items=[CourseRead.model_validate(c) for c in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post("", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
async def create_course(data: CourseCreate, ctx: TenantManager, db: DBSession) -> CourseRead:
    course = await CourseService(db, ctx.tenant_id).create(data, created_by_id=ctx.user.id)
    return CourseRead.model_validate(course)


@router.get("/{course_id}", response_model=CourseRead)
async def get_course(course_id: uuid.UUID, ctx: TenantMember, db: DBSession) -> CourseRead:
    course = await CourseService(db, ctx.tenant_id).get(course_id)
    return CourseRead.model_validate(course)


@router.patch("/{course_id}", response_model=CourseRead)
async def update_course(
    course_id: uuid.UUID, data: CourseUpdate, ctx: TenantManager, db: DBSession
) -> CourseRead:
    course = await CourseService(db, ctx.tenant_id).update(course_id, data)
    return CourseRead.model_validate(course)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(course_id: uuid.UUID, ctx: TenantManager, db: DBSession) -> None:
    await CourseService(db, ctx.tenant_id).delete(course_id)
