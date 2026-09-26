import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enrollment import ProgressStatus
from app.schemas.common import ORMModel


class EnrollmentCreate(BaseModel):
    user_id: uuid.UUID


class ProgressUpdate(BaseModel):
    progress_percent: int = Field(ge=0, le=100)


class EnrollmentRead(ORMModel):
    id: uuid.UUID
    course_id: uuid.UUID
    user_id: uuid.UUID
    status: ProgressStatus
    progress_percent: int
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
