import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppError, ForbiddenError, TrialExpiredError, UnauthorizedError
from app.core.security import decode_access_token
from app.models.tenant import Tenant
from app.models.user import PlatformRole, TenantRole, User
from app.repositories import TenantRepository, UserRepository
from app.schemas.common import PaginationParams

DBSession = Annotated[AsyncSession, Depends(get_db)]

_bearer = HTTPBearer(auto_error=False)

# Platform roles that may invite a tenant's tenantadmins.
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
    def is_platform(self) -> bool:
        return self.user.platform_role is not None

    @property
    def trial_expired(self) -> bool:
        return self.tenant.trial_expired

    @property
    def can_manage(self) -> bool:
        return not self.is_platform and self.user.tenant_role == TenantRole.TENANTADMIN

    @property
    def can_invite(self) -> bool:
        # Platform managers may invite (tenantadmins only; enforced at the endpoint).
        return self.can_manage or self.user.platform_role in _PLATFORM_MANAGERS


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

    # Platform roles reach every tenant's metadata, including deactivated tenants.
    if user.platform_role is not None:
        return TenantContext(user=user, tenant=tenant)

    # A tenant account only ever reaches its own tenant.
    if user.tenant_id != tenant.id or user.tenant_role is None or not tenant.is_active:
        raise no_access
    return TenantContext(user=user, tenant=tenant)


def _require(
    check: Callable[[TenantContext], bool], *, active_trial: bool = False
) -> Callable[..., Awaitable[TenantContext]]:
    """active_trial: also refuse once the tenant's trial is over (learning features, invites)."""

    async def checker(ctx: Annotated[TenantContext, Depends(get_tenant_context)]) -> TenantContext:
        if not check(ctx):
            raise ForbiddenError("Insufficient permissions")
        if active_trial and ctx.trial_expired:
            raise TrialExpiredError("This organization's trial has expired")
        return ctx

    return checker


# Tenant metadata only: the tenant's own accounts plus any platform role.
TenantScope = Annotated[TenantContext, Depends(get_tenant_context)]
# The tenant's own accounts. Platform roles never see tenant data (users' PII, courses).
TenantMember = Annotated[TenantContext, Depends(_require(lambda c: not c.is_platform))]
# The tenant's own tenantadmins.
TenantManager = Annotated[TenantContext, Depends(_require(lambda c: c.can_manage))]
TenantInviter = Annotated[
    TenantContext, Depends(_require(lambda c: c.can_invite, active_trial=True))
]
# Learning features (courses) additionally need a running trial. An expired tenant's accounts
# can still sign in, see the tenant's status and manage (not invite) users.
LearningMember = Annotated[
    TenantContext, Depends(_require(lambda c: not c.is_platform, active_trial=True))
]
LearningManager = Annotated[
    TenantContext, Depends(_require(lambda c: c.can_manage, active_trial=True))
]


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
