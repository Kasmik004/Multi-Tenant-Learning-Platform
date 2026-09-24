from fastapi import APIRouter, status

from app.api.deps import AdminUser, DBSession, Pagination
from app.schemas.common import Page
from app.schemas.user import UserCreate, UserRead
from app.services import UserService

router = APIRouter()


@router.get("", response_model=Page[UserRead])
async def list_users(admin: AdminUser, db: DBSession, page: Pagination) -> Page[UserRead]:
    items, total = await UserService(db, admin.tenant_id).list(limit=page.limit, offset=page.offset)
    return Page(
        items=[UserRead.model_validate(u) for u in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate, admin: AdminUser, db: DBSession) -> UserRead:
    user = await UserService(db, admin.tenant_id).create(data)
    return UserRead.model_validate(user)
