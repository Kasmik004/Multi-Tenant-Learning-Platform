import uuid

from fastapi import APIRouter, status

from app.api.deps import DBSession, Pagination, TenantManager, TenantOverseer
from app.schemas.common import Page
from app.schemas.user import InviteCreate, InviteRead, UserRead, UserUpdate
from app.services import UserService

router = APIRouter()


@router.get("", response_model=Page[UserRead])
async def list_users(ctx: TenantOverseer, db: DBSession, page: Pagination) -> Page[UserRead]:
    items, total = await UserService(db, ctx.tenant_id).list(limit=page.limit, offset=page.offset)
    return Page(
        items=[UserRead.model_validate(u) for u in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post("/invites", response_model=InviteRead, status_code=status.HTTP_201_CREATED)
async def invite_user(data: InviteCreate, ctx: TenantManager, db: DBSession) -> InviteRead:
    return await UserService(db, ctx.tenant_id).invite(data)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: uuid.UUID, data: UserUpdate, ctx: TenantManager, db: DBSession
) -> UserRead:
    return UserRead.model_validate(
        await UserService(db, ctx.tenant_id).set_role(user_id, data.role)
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user(user_id: uuid.UUID, ctx: TenantManager, db: DBSession) -> None:
    await UserService(db, ctx.tenant_id).remove(user_id)
