import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.user import PlatformRole, TenantRole
from app.schemas.common import ORMModel


class UserRead(ORMModel):
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    email: EmailStr
    full_name: str | None
    tenant_role: TenantRole | None
    platform_role: PlatformRole | None
    is_active: bool
    invite_pending: bool
    created_at: datetime


class MeRead(UserRead):
    # Send this as X-Tenant-Slug; None for platform accounts.
    tenant_slug: str | None


class InviteCreate(BaseModel):
    email: EmailStr
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    role: TenantRole = TenantRole.USER


class InviteRead(BaseModel):
    user: UserRead
    # Shown once; only its hash is stored. Delivered by email once that exists.
    invite_token: str
    invite_expires_at: datetime


class UserUpdate(BaseModel):
    role: TenantRole
