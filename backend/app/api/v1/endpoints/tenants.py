from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DBSession
from app.core.exceptions import NotFoundError
from app.repositories import TenantRepository
from app.schemas.tenant import TenantCreate, TenantRead
from app.services import TenantService

router = APIRouter()


# NOTE: open for self-service onboarding. Restrict (platform-admin auth, invite codes,
# rate limiting) before exposing publicly.
@router.post("", response_model=TenantRead, status_code=status.HTTP_201_CREATED)
async def create_tenant(data: TenantCreate, db: DBSession) -> TenantRead:
    tenant = await TenantService(db).create_with_admin(data)
    return TenantRead.model_validate(tenant)


@router.get("/current", response_model=TenantRead)
async def current_tenant(user: CurrentUser, db: DBSession) -> TenantRead:
    tenant = await TenantRepository(db).get(user.tenant_id)
    if tenant is None:
        raise NotFoundError("Tenant not found")
    return TenantRead.model_validate(tenant)
