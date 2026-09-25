from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedError
from app.core.security import (
    create_access_token,
    hash_invite_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories import TenantRepository, UserRepository
from app.schemas.auth import AcceptInviteRequest, LoginRequest, Token
from app.schemas.user import MeRead, UserRead


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def login(self, data: LoginRequest) -> Token:
        # Same error for every failure so callers can't probe which tenants/emails exist.
        invalid = UnauthorizedError("Invalid credentials")

        tenant_id = None
        if data.tenant_slug:
            tenant = await TenantRepository(self.session).get_by_slug(data.tenant_slug)
            if tenant is None or not tenant.is_active:
                raise invalid
            tenant_id = tenant.id

        user = await self.users.get_for_login(data.email, tenant_id)
        if user is None or not user.is_active or user.hashed_password is None:
            raise invalid
        # Without a tenant only platform accounts may sign in.
        if tenant_id is None and user.platform_role is None:
            raise invalid
        if not verify_password(data.password, user.hashed_password):
            raise invalid

        return Token(access_token=create_access_token(user_id=user.id))

    async def accept_invite(self, data: AcceptInviteRequest) -> Token:
        user = await self.users.get_by_invite_hash(hash_invite_token(data.token))
        if (
            user is None
            or user.invite_expires_at is None
            or user.invite_expires_at < datetime.now(UTC)
        ):
            raise UnauthorizedError("Invalid or expired invite")

        user.hashed_password = hash_password(data.password)
        # Single use: the token can't be replayed once accepted.
        user.invite_token_hash = None
        user.invite_expires_at = None
        await self.session.commit()
        return Token(access_token=create_access_token(user_id=user.id))

    async def me(self, user: User) -> MeRead:
        tenant = (
            await TenantRepository(self.session).get(user.tenant_id) if user.tenant_id else None
        )
        return MeRead(
            **UserRead.model_validate(user).model_dump(),
            tenant_slug=tenant.slug if tenant else None,
        )
