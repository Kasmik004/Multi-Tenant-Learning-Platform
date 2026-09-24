import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.models.user import User, UserRole
from app.repositories import UserRepository
from app.schemas.common import PaginationParams

DBSession = Annotated[AsyncSession, Depends(get_db)]

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    db: DBSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise UnauthorizedError("Not authenticated")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
        tenant_id = uuid.UUID(payload["tid"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise UnauthorizedError("Invalid or expired token") from exc

    # Lookup is tenant-scoped, so a token can never resolve to a user in another tenant.
    user = await UserRepository(db, tenant_id).get(user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Invalid or expired token")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[[User], Awaitable[User]]:
    """Dependency factory: `Depends(require_roles(UserRole.ADMIN))`."""

    async def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise ForbiddenError("Insufficient permissions")
        return user

    return checker


AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]
StaffUser = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.INSTRUCTOR))]

Pagination = Annotated[PaginationParams, Depends()]
