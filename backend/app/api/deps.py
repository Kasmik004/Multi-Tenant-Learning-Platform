import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppError, ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.models.tenant import Tenant
from app.models.user import PlatformRole, TenantRole, User
from app.repositories import TenantRepository, UserRepository
from app.schemas.common import PaginationParams

DBSession = Annotated[AsyncSession, Depends(get_db)]

_bearer = HTTPBearer(auto_error=False)

# Platform roles that may write inside any tenant; superviewer is read-only.
_PLATFORM_MANAGERS = {PlatformRole.SUPERADMIN, PlatformRole.ADMIN}


async def get_current_user(
    db: DBSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise UnauthorizedError("Not authenticated")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise UnauthorizedError("Invalid or expired token") from exc

    user = await UserRepository(db).get(user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Invalid or expired token")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


@dataclass(frozen=True)
class TenantContext:
    """Who is acting, in which tenant (from X-Tenant-Slug), and with what rights."""

    user: User
    tenant: Tenant

    @property
    def tenant_id(self) -> uuid.UUID:
        return self.tenant.id

    @property
    def can_manage(self) -> bool:
        if self.user.platform_role in _PLATFORM_MANAGERS:
            return True
        return self.user.tenant_role == TenantRole.TENANTADMIN

    @property
    def can_oversee(self) -> bool:
        """Read tenant admin data (the user list): managers plus superviewer."""
        return self.can_manage or self.user.platform_role == PlatformRole.SUPERVIEWER


async def get_tenant_context(
    user: CurrentUser,
    db: DBSession,
    x_tenant_slug: Annotated[str | None, Header()] = None,
) -> TenantContext:
    if not x_tenant_slug:
        raise AppError("X-Tenant-Slug header is required")

    # Same error for unknown tenants and other tenants so the header can't probe slugs.
    no_access = ForbiddenError("You don't have access to this tenant")
    tenant = await TenantRepository(db).get_by_slug(x_tenant_slug)
    if tenant is None:
        raise no_access

    # Platform roles reach every tenant, including deactivated ones they need to manage.
    if user.platform_role is not None:
        return TenantContext(user=user, tenant=tenant)

    # A tenant account only ever reaches its own tenant.
    if user.tenant_id != tenant.id or user.tenant_role is None or not tenant.is_active:
        raise no_access
    return TenantContext(user=user, tenant=tenant)


async def require_tenant_manager(
    ctx: Annotated[TenantContext, Depends(get_tenant_context)],
) -> TenantContext:
    if not ctx.can_manage:
        raise ForbiddenError("Insufficient permissions")
    return ctx


async def require_tenant_overseer(
    ctx: Annotated[TenantContext, Depends(get_tenant_context)],
) -> TenantContext:
    if not ctx.can_oversee:
        raise ForbiddenError("Insufficient permissions")
    return ctx


# Any active member of the tenant, or any platform role (superviewer included).
TenantMember = Annotated[TenantContext, Depends(get_tenant_context)]
# tenantadmin of the tenant, or superadmin/admin.
TenantManager = Annotated[TenantContext, Depends(require_tenant_manager)]
# TenantManager plus read-only superviewer.
TenantOverseer = Annotated[TenantContext, Depends(require_tenant_overseer)]


def require_platform_roles(*roles: PlatformRole) -> Callable[[User], Awaitable[User]]:
    """Dependency factory: `Depends(require_platform_roles(PlatformRole.SUPERADMIN))`."""

    async def checker(user: CurrentUser) -> User:
        if user.platform_role not in roles:
            raise ForbiddenError("Insufficient permissions")
        return user

    return checker


SuperAdminUser = Annotated[User, Depends(require_platform_roles(PlatformRole.SUPERADMIN))]
PlatformAdminUser = Annotated[
    User, Depends(require_platform_roles(PlatformRole.SUPERADMIN, PlatformRole.ADMIN))
]
PlatformUser = Annotated[User, Depends(require_platform_roles(*PlatformRole))]


Pagination = Annotated[PaginationParams, Depends()]
