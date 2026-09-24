from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.repositories import TenantRepository, UserRepository
from app.schemas.tenant import TenantCreate


class TenantService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.tenants = TenantRepository(session)

    async def create_with_admin(self, data: TenantCreate) -> Tenant:
        if await self.tenants.get_by_slug(data.slug):
            raise ConflictError(f"Tenant slug '{data.slug}' is already taken")

        try:
            tenant = await self.tenants.add(Tenant(name=data.name, slug=data.slug))
            await UserRepository(self.session, tenant.id).add(
                User(
                    email=data.admin.email.lower(),
                    full_name=data.admin.full_name,
                    hashed_password=hash_password(data.admin.password),
                    role=UserRole.ADMIN,
                )
            )
            await self.session.commit()
        except IntegrityError as exc:  # lost a race on the unique slug
            await self.session.rollback()
            raise ConflictError(f"Tenant slug '{data.slug}' is already taken") from exc
        return tenant
