from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.tenant import Tenant
from app.repositories import TenantRepository
from app.schemas.tenant import TenantCreate, TenantUpdate


class TenantService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.tenants = TenantRepository(session)

    async def create(self, data: TenantCreate) -> Tenant:
        if await self.tenants.get_by_slug(data.slug):
            raise ConflictError(f"Tenant slug '{data.slug}' is already taken")

        try:
            tenant = await self.tenants.add(Tenant(name=data.name, slug=data.slug))
            await self.session.commit()
        except IntegrityError as exc:  # lost a race on the unique slug
            await self.session.rollback()
            raise ConflictError(f"Tenant slug '{data.slug}' is already taken") from exc
        return tenant

    async def list(self, *, limit: int, offset: int) -> tuple[list[Tenant], int]:
        return await self.tenants.list(limit=limit, offset=offset)

    async def get_by_slug(self, slug: str) -> Tenant:
        tenant = await self.tenants.get_by_slug(slug)
        if tenant is None:
            raise NotFoundError("Tenant not found")
        return tenant

    async def update(self, slug: str, data: TenantUpdate) -> Tenant:
        tenant = await self.get_by_slug(slug)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(tenant, field, value)
        await self.session.commit()
        await self.session.refresh(tenant)
        return tenant

    async def delete(self, slug: str) -> None:
        await self.tenants.delete(await self.get_by_slug(slug))
        await self.session.commit()
