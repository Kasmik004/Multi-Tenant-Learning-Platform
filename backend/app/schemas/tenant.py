import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.tenant import TenantStatus
from app.schemas.common import ORMModel

SLUG_PATTERN = r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"


class TenantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(pattern=SLUG_PATTERN)


class TenantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    is_active: bool | None = None


class TrialExtend(BaseModel):
    days: int = Field(ge=1, le=365)


class TenantRead(ORMModel):
    id: uuid.UUID
    name: str
    slug: str
    is_active: bool
    # Live status: already "expired" once trial_ends_at passes, even before the sweep runs.
    status: TenantStatus = Field(validation_alias="current_status")
    trial_ends_at: datetime
    expired_at: datetime | None
    created_at: datetime
