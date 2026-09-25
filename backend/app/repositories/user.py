import uuid

from sqlalchemy import select

from app.models.user import User
from app.repositories.base import BaseRepository, TenantScopedRepository


class UserRepository(BaseRepository[User]):
    """Unscoped lookups for authentication only. Tenant features use TenantUserRepository."""

    model = User

    async def get_for_login(self, email: str, tenant_id: uuid.UUID | None) -> User | None:
        # tenant_id None means a platform account.
        tenant_match = User.tenant_id == tenant_id if tenant_id else User.tenant_id.is_(None)
        result = await self.session.execute(
            select(User).where(User.email == email.lower(), tenant_match)
        )
        return result.scalar_one_or_none()

    async def get_by_invite_hash(self, token_hash: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.invite_token_hash == token_hash)
        )
        return result.scalar_one_or_none()


class TenantUserRepository(TenantScopedRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(self._query().where(User.email == email.lower()))
        return result.scalar_one_or_none()
