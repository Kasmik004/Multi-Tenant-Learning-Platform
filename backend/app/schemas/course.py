import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class CourseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    is_published: bool = False


class CourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    is_published: bool | None = None


class CourseRead(ORMModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    description: str | None
    is_published: bool
    created_by_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
