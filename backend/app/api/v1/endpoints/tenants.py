from fastapi import APIRouter, status

from app.api.deps import (
    DBSession,
    Pagination,
    PlatformAdminUser,
    PlatformUser,
    SuperAdminUser,
    TenantScope,
)
from app.schemas.common import Page
from app.schemas.tenant import TenantCreate, TenantRead, TenantUpdate, TrialExtend
from app.services import TenantService

router = APIRouter()


@router.post("", response_model=TenantRead, status_code=status.HTTP_201_CREATED)
async def create_tenant(data: TenantCreate, _: SuperAdminUser, db: DBSession) -> TenantRead:
    tenant = await TenantService(db).create(data)
    return TenantRead.model_validate(tenant)


@router.get("", response_model=Page[TenantRead])
async def list_tenants(_: PlatformUser, db: DBSession, page: Pagination) -> Page[TenantRead]:
    items, total = await TenantService(db).list(limit=page.limit, offset=page.offset)
    return Page(
        items=[TenantRead.model_validate(t) for t in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/current", response_model=TenantRead)
async def current_tenant(ctx: TenantScope) -> TenantRead:
    return TenantRead.model_validate(ctx.tenant)


@router.get("/{slug}", response_model=TenantRead)
async def get_tenant(slug: str, _: PlatformUser, db: DBSession) -> TenantRead:
    return TenantRead.model_validate(await TenantService(db).get_by_slug(slug))


@router.patch("/{slug}", response_model=TenantRead)
async def update_tenant(
    slug: str, data: TenantUpdate, _: PlatformAdminUser, db: DBSession
) -> TenantRead:
    return TenantRead.model_validate(await TenantService(db).update(slug, data))


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(slug: str, _: SuperAdminUser, db: DBSession) -> None:
    await TenantService(db).delete(slug)


@router.post("/{slug}/trial", response_model=TenantRead)
async def extend_trial(
    slug: str, data: TrialExtend, _: PlatformAdminUser, db: DBSession
) -> TenantRead:
    """Extends the trial by `days`; reactivates an expired tenant (counted from now)."""
    return TenantRead.model_validate(await TenantService(db).extend_trial(slug, data.days))
