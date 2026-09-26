from fastapi import APIRouter

from app.api.deps import DBSession, LearningMember, Pagination
from app.schemas.common import Page
from app.schemas.enrollment import EnrollmentRead
from app.services import EnrollmentService

router = APIRouter()


@router.get("/me", response_model=Page[EnrollmentRead])
async def my_enrollments(
    ctx: LearningMember, db: DBSession, page: Pagination
) -> Page[EnrollmentRead]:
    """The caller's assigned (published) courses with their progress, oldest first."""
    items, total = await EnrollmentService(db, ctx.tenant_id).list_own(
        ctx.user.id, limit=page.limit, offset=page.offset
    )
    return Page(
        items=[EnrollmentRead.model_validate(e) for e in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )
