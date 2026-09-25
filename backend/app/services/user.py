import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import new_invite_token
from app.models.user import TenantRole, User
from app.repositories import TenantUserRepository
from app.schemas.user import InviteCreate, InviteRead, UserRead


class UserService:
    """Tenant-scoped user management: every lookup is filtered by the caller's tenant."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self.session = session
        self.users = TenantUserRepository(session, tenant_id)

    async def list(self, *, limit: int, offset: int) -> tuple[list[User], int]:
        return await self.users.list(limit=limit, offset=offset)

    async def get(self, user_id: uuid.UUID) -> User:
        user = await self.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user

    async def invite(self, data: InviteCreate) -> InviteRead:
        user = await self.users.get_by_email(data.email)
        if user is not None and not user.invite_pending:
            raise ConflictError("A user with this email already exists in this tenant")

        token, token_hash = new_invite_token()
        expires_at = datetime.now(UTC) + timedelta(hours=settings.INVITE_EXPIRE_HOURS)
        try:
            if user is None:
                user = await self.users.add(User(email=data.email.lower()))
            # Re-inviting a pending user replaces the old token, which stops working.
            user.full_name = data.full_name
            user.tenant_role = data.role
            user.invite_token_hash = token_hash
            user.invite_expires_at = expires_at
            await self.session.commit()
        except IntegrityError as exc:  # lost a race on the unique (tenant, email)
            await self.session.rollback()
            raise ConflictError("A user with this email already exists in this tenant") from exc

        await self.session.refresh(user)
        return InviteRead(
            user=UserRead.model_validate(user), invite_token=token, invite_expires_at=expires_at
        )

    async def set_role(self, user_id: uuid.UUID, role: TenantRole) -> User:
        user = await self.get(user_id)
        user.tenant_role = role
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def remove(self, user_id: uuid.UUID) -> None:
        await self.users.delete(await self.get(user_id))
        await self.session.commit()
