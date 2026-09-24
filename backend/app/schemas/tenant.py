import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel

SLUG_PATTERN = r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"


class TenantAdminCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=128)


class TenantCreate(BaseModel):
    """Onboards an organization together with its first administrator."""

    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(pattern=SLUG_PATTERN)
    admin: TenantAdminCreate


class TenantRead(ORMModel):
    id: uuid.UUID
    name: str
    slug: str
    is_active: bool
    created_at: datetime
