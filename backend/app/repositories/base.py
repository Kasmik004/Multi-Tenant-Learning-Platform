import uuid
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base


class BaseRepository[ModelT: Base]:
    """Generic data access. Repositories flush but never commit; services own transactions."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _query(self) -> Select[tuple[ModelT]]:
        return select(self.model)

    async def get(self, id: uuid.UUID) -> ModelT | None:
        pk: Any = self.model.id  # type: ignore[attr-defined]
        result = await self.session.execute(self._query().where(pk == id))
        return result.scalar_one_or_none()

    async def list(self, *, limit: int = 50, offset: int = 0) -> tuple[list[ModelT], int]:
        query = self._query()
        total = await self.session.scalar(select(func.count()).select_from(query.subquery()))
        rows = await self.session.scalars(query.limit(limit).offset(offset))
        return list(rows), total or 0

    async def add(self, obj: ModelT) -> ModelT:
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self.session.delete(obj)
        await self.session.flush()


class TenantScopedRepository[ModelT: Base](BaseRepository[ModelT]):
    """Every query is constrained to one tenant, so cross-tenant reads are impossible by default.

    Use this for any model with TenantScopedMixin.
    """

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(session)
        self.tenant_id = tenant_id

    def _query(self) -> Select[tuple[ModelT]]:
        tenant_col: Any = self.model.tenant_id  # type: ignore[attr-defined]
        return super()._query().where(tenant_col == self.tenant_id)

    async def add(self, obj: ModelT) -> ModelT:
        obj.tenant_id = self.tenant_id  # type: ignore[attr-defined]
        return await super().add(obj)
