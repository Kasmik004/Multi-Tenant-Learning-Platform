import logging
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError
from app.models.tenant import Tenant, TenantStatus
from app.repositories import TenantRepository
from app.schemas.tenant import TenantCreate, TenantUpdate

logger = logging.getLogger(__name__)


class TenantService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.tenants = TenantRepository(session)

    async def create(self, data: TenantCreate) -> Tenant:
        if await self.tenants.get_by_slug(data.slug):
            raise ConflictError(f"Tenant slug '{data.slug}' is already taken")

        # Created -> trial_active in one step: the free trial starts now.
        trial_ends_at = datetime.now(UTC) + timedelta(days=settings.TRIAL_DAYS)
        try:
            tenant = await self.tenants.add(
                Tenant(name=data.name, slug=data.slug, trial_ends_at=trial_ends_at)
            )
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

    async def extend_trial(self, slug: str, days: int) -> Tenant:
        """Adds `days` to the trial; an expired tenant gets `days` from now and is reactivated.

        Extending never shortens a running trial.
        """
        tenant = await self.get_by_slug(slug)
        now = datetime.now(UTC)
        tenant.trial_ends_at = max(tenant.trial_ends_at, now) + timedelta(days=days)
        tenant.status = TenantStatus.TRIAL_ACTIVE
        tenant.expired_at = None
        await self.session.commit()
        await self.session.refresh(tenant)
        logger.info("Trial for tenant %s extended to %s", slug, tenant.trial_ends_at)
        return tenant

    async def expire_trials(self, now: datetime | None = None) -> Sequence[str]:
        """Records every trial that has run out; returns the slugs expired by *this* call.

        Safe to run repeatedly or concurrently: one conditional UPDATE only touches tenants
        still marked trial_active, so each expiry is recorded exactly once.
        """
        now = now or datetime.now(UTC)
        result = await self.session.execute(
            update(Tenant)
            .where(Tenant.status == TenantStatus.TRIAL_ACTIVE, Tenant.trial_ends_at <= now)
            .values(status=TenantStatus.EXPIRED, expired_at=now)
            .returning(Tenant.slug)
        )
        slugs = list(result.scalars())
        await self.session.commit()
        for slug in slugs:
            logger.info("Trial for tenant %s expired", slug)
        return slugs
